"""
PDF report generation for municipality profiles.
"""

import io
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models.municipality import Canton, Municipality
from app.models.financial import FinancialData
from app.models.demographic import DemographicData
from app.models.scores import CompositeScore

router = APIRouter()


def _build_pdf(data: dict) -> bytes:
    """
    Generate a municipality profile PDF using reportlab.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=6,
        textColor=colors.HexColor("#1a1a2e"),
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor("#0f3460"),
    )
    body_style = styles["Normal"]

    elements = []

    # Title
    muni = data["municipality"]
    elements.append(Paragraph(f"{muni['name']}", title_style))
    elements.append(Paragraph(
        f"{muni['canton_name']} ({muni['canton']}) | BFS {muni['bfs_number']}",
        body_style,
    ))
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f3460")))
    elements.append(Spacer(1, 4 * mm))

    # Overview
    elements.append(Paragraph("Overview", heading_style))
    overview_data = [
        ["Population", f"{muni.get('population', '—'):,}" if muni.get("population") else "—"],
        ["Area", f"{muni.get('area_km2', '—')} km²" if muni.get("area_km2") else "—"],
        ["Type", muni.get("municipality_type", "—") or "—"],
    ]
    overview_table = Table(overview_data, colWidths=[50 * mm, 100 * mm])
    overview_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(overview_table)

    # Composite Scores
    scores = data.get("scores")
    if scores:
        elements.append(Paragraph(f"Composite Scores ({scores.get('year', '—')})", heading_style))
        score_data = [
            ["Dimension", "Score", "Rank"],
            ["Overall Composite", _fmt(scores.get("composite_score")), _fmt(scores.get("national_rank"))],
            ["Financial Health", _fmt(scores.get("financial_health_score")), ""],
            ["Tax Attractiveness", _fmt(scores.get("tax_attractiveness_score")), ""],
            ["Demographic Vitality", _fmt(scores.get("demographic_vitality_score")), ""],
            ["Economic Strength", _fmt(scores.get("economic_strength_score")), ""],
        ]
        score_table = Table(score_data, colWidths=[60 * mm, 40 * mm, 40 * mm])
        score_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f4f8")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(score_table)
        if scores.get("peer_group"):
            elements.append(Paragraph(
                f"Peer Group: {scores['peer_group']} (Rank #{scores.get('peer_group_rank', '—')})",
                body_style,
            ))

    # Financial Data
    financials = data.get("financials", [])
    if financials:
        elements.append(Paragraph("Financial History", heading_style))
        fin_header = ["Year", "Revenue p.c.", "Expend. p.c.", "Net Debt p.c.", "Self-Fin. Ratio"]
        fin_rows = [fin_header]
        for f in financials[-10:]:  # Last 10 years
            fin_rows.append([
                str(f.get("year", "")),
                _fmt_chf(f.get("revenue_per_capita")),
                _fmt_chf(f.get("expenditure_per_capita")),
                _fmt_chf(f.get("net_debt_per_capita")),
                _fmt_pct(f.get("self_financing_ratio")),
            ])
        fin_table = Table(fin_rows, colWidths=[25 * mm, 35 * mm, 35 * mm, 35 * mm, 35 * mm])
        fin_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f4f8")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(fin_table)

    # Demographics
    demographics = data.get("demographics", [])
    if demographics:
        elements.append(Paragraph("Demographic History", heading_style))
        dem_header = ["Year", "Population", "Growth %", "Foreign %", "Dep. Ratio"]
        dem_rows = [dem_header]
        for d in demographics[-10:]:
            dem_rows.append([
                str(d.get("year", "")),
                f"{d['population_total']:,}" if d.get("population_total") else "—",
                _fmt_pct(d.get("population_growth_rate")),
                _fmt_pct(d.get("foreign_share")),
                _fmt_pct(d.get("dependency_ratio")),
            ])
        dem_table = Table(dem_rows, colWidths=[25 * mm, 35 * mm, 30 * mm, 30 * mm, 30 * mm])
        dem_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f4f8")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(dem_table)

    # Footer
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Paragraph(
        "Generated by Swiss Municipality Analytics Platform",
        ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=colors.grey),
    ))

    doc.build(elements)
    return buffer.getvalue()


def _fmt(val) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        return f"{val:.1f}"
    return str(val)


def _fmt_chf(val) -> str:
    if val is None:
        return "—"
    return f"CHF {val:,.0f}"


def _fmt_pct(val) -> str:
    if val is None:
        return "—"
    return f"{val:.1f}%"


@router.get("/{bfs_number}/pdf")
async def generate_municipality_report(
    bfs_number: int,
    db: AsyncSession = Depends(get_db),
):
    """Generate a comprehensive PDF report for a municipality."""
    # Fetch municipality details
    query = (
        select(Municipality)
        .options(joinedload(Municipality.canton))
        .where(Municipality.bfs_number == bfs_number)
    )
    result = await db.execute(query)
    muni = result.scalar_one_or_none()
    if not muni:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Municipality {bfs_number} not found")

    # Fetch financial data
    fin_query = (
        select(FinancialData)
        .where(FinancialData.municipality_bfs == bfs_number)
        .order_by(FinancialData.year)
    )
    fin_result = await db.execute(fin_query)
    financials = fin_result.scalars().all()

    # Fetch demographic data
    dem_query = (
        select(DemographicData)
        .where(DemographicData.municipality_bfs == bfs_number)
        .order_by(DemographicData.year)
    )
    dem_result = await db.execute(dem_query)
    demographics = dem_result.scalars().all()

    # Fetch scores
    score_query = (
        select(CompositeScore)
        .where(CompositeScore.municipality_bfs == bfs_number)
        .order_by(CompositeScore.year.desc())
    )
    score_result = await db.execute(score_query)
    scores_list = score_result.scalars().all()
    latest_score = scores_list[0] if scores_list else None

    # Build data dict
    data = {
        "municipality": {
            "bfs_number": muni.bfs_number,
            "name": muni.name,
            "canton": muni.canton.abbreviation,
            "canton_name": muni.canton.name_de,
            "population": muni.population,
            "area_km2": float(muni.area_km2) if muni.area_km2 else None,
            "municipality_type": muni.municipality_type,
        },
        "scores": {
            "year": latest_score.year,
            "composite_score": float(latest_score.composite_score) if latest_score and latest_score.composite_score else None,
            "financial_health_score": float(latest_score.financial_health_score) if latest_score and latest_score.financial_health_score else None,
            "tax_attractiveness_score": float(latest_score.tax_attractiveness_score) if latest_score and latest_score.tax_attractiveness_score else None,
            "demographic_vitality_score": float(latest_score.demographic_vitality_score) if latest_score and latest_score.demographic_vitality_score else None,
            "economic_strength_score": float(latest_score.economic_strength_score) if latest_score and latest_score.economic_strength_score else None,
            "national_rank": int(latest_score.national_rank) if latest_score and latest_score.national_rank else None,
            "peer_group": latest_score.peer_group if latest_score else None,
            "peer_group_rank": int(latest_score.peer_group_rank) if latest_score and latest_score.peer_group_rank else None,
        } if latest_score else None,
        "financials": [
            {
                "year": f.year,
                "revenue_per_capita": float(f.revenue_per_capita) if f.revenue_per_capita else None,
                "expenditure_per_capita": float(f.expenditure_per_capita) if f.expenditure_per_capita else None,
                "net_debt_per_capita": float(f.net_debt_per_capita) if f.net_debt_per_capita else None,
                "self_financing_ratio": float(f.self_financing_ratio) if f.self_financing_ratio else None,
            }
            for f in financials
        ],
        "demographics": [
            {
                "year": d.year,
                "population_total": d.population_total,
                "population_growth_rate": float(d.population_growth_rate) if d.population_growth_rate else None,
                "foreign_share": float(d.foreign_share) if d.foreign_share else None,
                "dependency_ratio": float(d.dependency_ratio) if d.dependency_ratio else None,
            }
            for d in demographics
        ],
    }

    pdf_bytes = _build_pdf(data)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{muni.name.replace(" ", "_")}_report.pdf"',
        },
    )
