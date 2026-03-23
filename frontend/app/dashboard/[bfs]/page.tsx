"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { api, FinancialData, CompositeScore, TimeSeriesPoint } from "@/lib/api";
import { ScoreCard } from "@/components/ui/ScoreCard";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";

interface MunicipalityDetail {
  bfs_number: number;
  name: string;
  canton: { abbreviation: string; name_de: string };
  population: number | null;
  area_km2: number | null;
  altitude_m: number | null;
}

export default function DashboardPage() {
  const { bfs } = useParams<{ bfs: string }>();
  const bfsNumber = parseInt(bfs);

  const [municipality, setMunicipality] = useState<MunicipalityDetail | null>(null);
  const [financials, setFinancials] = useState<FinancialData[]>([]);
  const [scores, setScores] = useState<CompositeScore[]>([]);
  const [debtTimeseries, setDebtTimeseries] = useState<TimeSeriesPoint[]>([]);
  const [revenueTimeseries, setRevenueTimeseries] = useState<TimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isNaN(bfsNumber)) return;

    Promise.all([
      api.municipalities.get(bfsNumber).catch(() => null),
      api.financial.get(bfsNumber).catch(() => []),
      api.scores.get(bfsNumber).catch(() => []),
      api.financial.timeseries(bfsNumber, "net_debt_per_capita").catch(() => []),
      api.financial.timeseries(bfsNumber, "revenue_per_capita").catch(() => []),
    ]).then(([muni, fin, sc, debt, rev]) => {
      setMunicipality(muni as MunicipalityDetail);
      setFinancials(fin);
      setScores(sc);
      setDebtTimeseries(debt);
      setRevenueTimeseries(rev);
      setLoading(false);
    });
  }, [bfsNumber]);

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading municipality data...</div>;
  }

  if (!municipality) {
    return <div className="text-center py-12 text-red-500">Municipality {bfs} not found.</div>;
  }

  const latestScore = scores.length > 0 ? scores[scores.length - 1] : null;
  const latestFinancial = financials.length > 0 ? financials[financials.length - 1] : null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">{municipality.name}</h1>
        <p className="text-gray-500">
          {municipality.canton.name_de} ({municipality.canton.abbreviation})
          {" | "}BFS {municipality.bfs_number}
          {municipality.population && ` | ${municipality.population.toLocaleString("de-CH")} Einwohner`}
          {municipality.area_km2 && ` | ${municipality.area_km2} km²`}
        </p>
      </div>

      {/* Composite Scores */}
      {latestScore && (
        <section>
          <h2 className="text-xl font-semibold mb-4">Composite Score ({latestScore.year})</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <ScoreCard label="Overall" value={latestScore.composite_score} rank={latestScore.national_rank} />
            <ScoreCard label="Financial Health" value={latestScore.financial_health_score} />
            <ScoreCard label="Tax Attractiveness" value={latestScore.tax_attractiveness_score} />
            <ScoreCard label="Demographics" value={latestScore.demographic_vitality_score} />
            <ScoreCard label="Economy" value={latestScore.economic_strength_score} />
          </div>
        </section>
      )}

      {/* Financial Overview */}
      {latestFinancial && (
        <section>
          <h2 className="text-xl font-semibold mb-4">Financial Overview ({latestFinancial.year})</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="Revenue p.c."
              value={latestFinancial.revenue_per_capita}
              format="chf"
            />
            <MetricCard
              label="Expenditure p.c."
              value={latestFinancial.expenditure_per_capita}
              format="chf"
            />
            <MetricCard
              label="Net Debt p.c."
              value={latestFinancial.net_debt_per_capita}
              format="chf"
            />
            <MetricCard
              label="Self-Financing Ratio"
              value={latestFinancial.self_financing_ratio}
              format="pct"
            />
          </div>
        </section>
      )}

      {/* Time Series Charts */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {debtTimeseries.length > 0 && (
          <TimeSeriesChart
            title="Net Debt per Capita (CHF)"
            data={debtTimeseries}
            color="#ef4444"
          />
        )}
        {revenueTimeseries.length > 0 && (
          <TimeSeriesChart
            title="Revenue per Capita (CHF)"
            data={revenueTimeseries}
            color="#22c55e"
          />
        )}
      </section>
    </div>
  );
}

function MetricCard({
  label,
  value,
  format,
}: {
  label: string;
  value: number | null;
  format: "chf" | "pct" | "num";
}) {
  let display = "—";
  if (value !== null) {
    switch (format) {
      case "chf":
        display = `CHF ${value.toLocaleString("de-CH", { maximumFractionDigits: 0 })}`;
        break;
      case "pct":
        display = `${value.toFixed(1)}%`;
        break;
      default:
        display = value.toLocaleString("de-CH");
    }
  }

  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-xl font-semibold mt-1">{display}</div>
    </div>
  );
}
