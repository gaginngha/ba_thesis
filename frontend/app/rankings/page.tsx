"use client";

import { useState, useEffect } from "react";
import { api, CompositeScore, Canton } from "@/lib/api";
import Link from "next/link";

export default function RankingsPage() {
  const [scores, setScores] = useState<CompositeScore[]>([]);
  const [cantons, setCantons] = useState<Canton[]>([]);
  const [selectedCanton, setSelectedCanton] = useState("");
  const [sortBy, setSortBy] = useState("composite_score");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.municipalities.cantons().then(setCantons).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string> = { limit: "100", sort_by: sortBy };
    if (selectedCanton) params.canton = selectedCanton;

    api.scores
      .rankings(params)
      .then(setScores)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedCanton, sortBy]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Municipality Rankings</h1>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <select
          className="px-3 py-2 border rounded-lg"
          value={selectedCanton}
          onChange={(e) => setSelectedCanton(e.target.value)}
        >
          <option value="">All Cantons</option>
          {cantons.map((c) => (
            <option key={c.abbreviation} value={c.abbreviation}>
              {c.name_de} ({c.abbreviation})
            </option>
          ))}
        </select>

        <select
          className="px-3 py-2 border rounded-lg"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="composite_score">Composite Score</option>
          <option value="financial_health_score">Financial Health</option>
          <option value="tax_attractiveness_score">Tax Attractiveness</option>
          <option value="demographic_vitality_score">Demographics</option>
          <option value="economic_strength_score">Economy</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-gray-500">Loading rankings...</p>
      ) : (
        <div className="bg-white rounded-lg border overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-4 py-3 text-left">#</th>
                <th className="px-4 py-3 text-left">Municipality</th>
                <th className="px-4 py-3 text-left">Canton</th>
                <th className="px-4 py-3 text-right">Composite</th>
                <th className="px-4 py-3 text-right">Financial</th>
                <th className="px-4 py-3 text-right">Tax</th>
                <th className="px-4 py-3 text-right">Demographics</th>
                <th className="px-4 py-3 text-right">Economy</th>
                <th className="px-4 py-3 text-left">Peer Group</th>
              </tr>
            </thead>
            <tbody>
              {scores.map((s, i) => (
                <tr key={s.municipality_bfs} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/dashboard/${s.municipality_bfs}`}
                      className="text-swiss-accent hover:underline font-medium"
                    >
                      {s.municipality_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{s.canton_abbreviation}</td>
                  <td className="px-4 py-3 text-right font-semibold">
                    <ScoreBadge value={s.composite_score} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ScoreBadge value={s.financial_health_score} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ScoreBadge value={s.tax_attractiveness_score} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ScoreBadge value={s.demographic_vitality_score} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ScoreBadge value={s.economic_strength_score} />
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{s.peer_group}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ScoreBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="text-gray-300">—</span>;

  let color = "text-gray-700";
  if (value >= 75) color = "text-green-600";
  else if (value >= 50) color = "text-yellow-600";
  else if (value >= 25) color = "text-orange-600";
  else color = "text-red-600";

  return <span className={color}>{value.toFixed(1)}</span>;
}
