"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, FinancialData, CompositeScore, TimeSeriesPoint, PeerGroupBenchmark } from "@/lib/api";
import { ScoreCard } from "@/components/ui/ScoreCard";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { RadarChart } from "@/components/charts/RadarChart";

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
  const [populationTimeseries, setPopulationTimeseries] = useState<TimeSeriesPoint[]>([]);
  const [benchmark, setBenchmark] = useState<PeerGroupBenchmark | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isNaN(bfsNumber)) return;

    Promise.all([
      api.municipalities.get(bfsNumber).catch(() => null),
      api.financial.get(bfsNumber).catch(() => []),
      api.scores.get(bfsNumber).catch(() => []),
      api.financial.timeseries(bfsNumber, "net_debt_per_capita").catch(() => []),
      api.financial.timeseries(bfsNumber, "revenue_per_capita").catch(() => []),
      api.demographics.timeseries(bfsNumber, "population_total").catch(() => []),
      api.benchmark.peerGroup(bfsNumber).catch(() => null),
    ]).then(([muni, fin, sc, debt, rev, pop, bench]) => {
      setMunicipality(muni as MunicipalityDetail);
      setFinancials(fin);
      setScores(sc);
      setDebtTimeseries(debt);
      setRevenueTimeseries(rev);
      setPopulationTimeseries(pop);
      setBenchmark(bench as PeerGroupBenchmark | null);
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
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{municipality.name}</h1>
          <p className="text-gray-500">
            {municipality.canton.name_de} ({municipality.canton.abbreviation})
            {" | "}BFS {municipality.bfs_number}
            {municipality.population && ` | ${municipality.population.toLocaleString("de-CH")} Einwohner`}
            {municipality.area_km2 && ` | ${municipality.area_km2} km²`}
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={api.reports.downloadPdf(bfsNumber)}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-swiss-accent text-white rounded-lg text-sm font-medium hover:bg-swiss-dark transition"
          >
            Download PDF Report
          </a>
          <Link
            href={`/trends?bfs=${bfsNumber}`}
            className="px-4 py-2 border border-swiss-accent text-swiss-accent rounded-lg text-sm font-medium hover:bg-swiss-light transition"
          >
            Trend Analysis
          </Link>
        </div>
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

      {/* Radar Chart + Peer Group Benchmark */}
      {latestScore && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <RadarChart
            title="Score Profile"
            data={[
              { dimension: "Financial", value: latestScore.financial_health_score ?? 0 },
              { dimension: "Tax", value: latestScore.tax_attractiveness_score ?? 0 },
              { dimension: "Demographics", value: latestScore.demographic_vitality_score ?? 0 },
              { dimension: "Economy", value: latestScore.economic_strength_score ?? 0 },
            ]}
          />

          {benchmark && !("error" in benchmark) && (
            <div className="bg-white rounded-lg border p-6">
              <h3 className="text-sm font-medium text-gray-600 mb-4">
                Peer Group: {benchmark.peer_group} ({benchmark.peer_group_size} municipalities)
              </h3>
              <table className="w-full text-sm">
                <thead className="text-gray-500">
                  <tr>
                    <th className="text-left pb-2">Dimension</th>
                    <th className="text-right pb-2">You</th>
                    <th className="text-right pb-2">Avg</th>
                    <th className="text-right pb-2">Percentile</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { key: "composite_score", label: "Overall" },
                    { key: "financial_health_score", label: "Financial" },
                    { key: "tax_attractiveness_score", label: "Tax" },
                    { key: "demographic_vitality_score", label: "Demographics" },
                    { key: "economic_strength_score", label: "Economy" },
                  ].map(({ key, label }) => (
                    <tr key={key} className="border-t">
                      <td className="py-2">{label}</td>
                      <td className="py-2 text-right font-mono font-semibold">
                        {benchmark.scores[key]?.toFixed(1) ?? "—"}
                      </td>
                      <td className="py-2 text-right font-mono text-gray-500">
                        {benchmark.peer_group_avg[key]?.toFixed(1) ?? "—"}
                      </td>
                      <td className="py-2 text-right">
                        {benchmark.percentile_rank[key] !== null && benchmark.percentile_rank[key] !== undefined ? (
                          <span className={
                            benchmark.percentile_rank[key]! >= 75 ? "text-green-600 font-semibold" :
                            benchmark.percentile_rank[key]! >= 50 ? "text-yellow-600" :
                            "text-red-600"
                          }>
                            {benchmark.percentile_rank[key]!.toFixed(0)}th
                          </span>
                        ) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {benchmark.top_5_peers && benchmark.top_5_peers.length > 0 && (
                <div className="mt-4 pt-3 border-t">
                  <div className="text-xs text-gray-500 mb-2">Top peers in group:</div>
                  <div className="flex flex-wrap gap-1">
                    {benchmark.top_5_peers.map((p) => (
                      <Link
                        key={p.municipality_bfs}
                        href={`/dashboard/${p.municipality_bfs}`}
                        className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
                      >
                        {p.name} ({p.canton}) — {p.composite_score?.toFixed(1)}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* Financial Overview */}
      {latestFinancial && (
        <section>
          <h2 className="text-xl font-semibold mb-4">Financial Overview ({latestFinancial.year})</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="Revenue p.c." value={latestFinancial.revenue_per_capita} format="chf" />
            <MetricCard label="Expenditure p.c." value={latestFinancial.expenditure_per_capita} format="chf" />
            <MetricCard label="Net Debt p.c." value={latestFinancial.net_debt_per_capita} format="chf" />
            <MetricCard label="Self-Financing Ratio" value={latestFinancial.self_financing_ratio} format="pct" />
          </div>
        </section>
      )}

      {/* Time Series Charts */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {debtTimeseries.length > 0 && (
          <TimeSeriesChart title="Net Debt per Capita (CHF)" data={debtTimeseries} color="#ef4444" />
        )}
        {revenueTimeseries.length > 0 && (
          <TimeSeriesChart title="Revenue per Capita (CHF)" data={revenueTimeseries} color="#22c55e" />
        )}
        {populationTimeseries.length > 0 && (
          <TimeSeriesChart title="Population" data={populationTimeseries} color="#8b5cf6" />
        )}
        {scores.length > 1 && (
          <TimeSeriesChart
            title="Composite Score Over Time"
            data={scores.map((s) => ({ year: s.year, value: s.composite_score }))}
            color="#f59e0b"
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
