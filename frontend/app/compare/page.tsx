"use client";

import { useState } from "react";
import { api, Municipality, CompositeScore } from "@/lib/api";

export default function ComparePage() {
  const [searchA, setSearchA] = useState("");
  const [searchB, setSearchB] = useState("");
  const [resultsA, setResultsA] = useState<Municipality[]>([]);
  const [resultsB, setResultsB] = useState<Municipality[]>([]);
  const [selectedA, setSelectedA] = useState<Municipality | null>(null);
  const [selectedB, setSelectedB] = useState<Municipality | null>(null);
  const [scoresA, setScoresA] = useState<CompositeScore | null>(null);
  const [scoresB, setScoresB] = useState<CompositeScore | null>(null);

  async function handleSearch(query: string, setter: (m: Municipality[]) => void) {
    if (query.length < 2) { setter([]); return; }
    const results = await api.municipalities.list({ search: query, limit: "10" });
    setter(results);
  }

  async function selectMunicipality(
    m: Municipality,
    side: "A" | "B",
  ) {
    if (side === "A") {
      setSelectedA(m);
      setResultsA([]);
      setSearchA(m.name);
      const scores = await api.scores.get(m.bfs_number);
      setScoresA(scores.length > 0 ? scores[scores.length - 1] : null);
    } else {
      setSelectedB(m);
      setResultsB([]);
      setSearchB(m.name);
      const scores = await api.scores.get(m.bfs_number);
      setScoresB(scores.length > 0 ? scores[scores.length - 1] : null);
    }
  }

  const dimensions = [
    { key: "composite_score", label: "Composite Score" },
    { key: "financial_health_score", label: "Financial Health" },
    { key: "tax_attractiveness_score", label: "Tax Attractiveness" },
    { key: "demographic_vitality_score", label: "Demographic Vitality" },
    { key: "economic_strength_score", label: "Economic Strength" },
  ] as const;

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">Compare Municipalities</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Municipality A */}
        <div>
          <input
            type="text"
            placeholder="Search first municipality..."
            className="w-full px-4 py-3 rounded-lg border focus:border-swiss-accent outline-none"
            value={searchA}
            onChange={(e) => { setSearchA(e.target.value); handleSearch(e.target.value, setResultsA); }}
          />
          {resultsA.length > 0 && (
            <div className="mt-1 bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto">
              {resultsA.map((m) => (
                <button
                  key={m.bfs_number}
                  className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b last:border-0"
                  onClick={() => selectMunicipality(m, "A")}
                >
                  {m.name} ({m.canton_abbreviation})
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Municipality B */}
        <div>
          <input
            type="text"
            placeholder="Search second municipality..."
            className="w-full px-4 py-3 rounded-lg border focus:border-swiss-accent outline-none"
            value={searchB}
            onChange={(e) => { setSearchB(e.target.value); handleSearch(e.target.value, setResultsB); }}
          />
          {resultsB.length > 0 && (
            <div className="mt-1 bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto">
              {resultsB.map((m) => (
                <button
                  key={m.bfs_number}
                  className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b last:border-0"
                  onClick={() => selectMunicipality(m, "B")}
                >
                  {m.name} ({m.canton_abbreviation})
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Comparison Table */}
      {selectedA && selectedB && (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left">Dimension</th>
                <th className="px-6 py-3 text-center">{selectedA.name}</th>
                <th className="px-6 py-3 text-center">{selectedB.name}</th>
              </tr>
            </thead>
            <tbody>
              {dimensions.map(({ key, label }) => {
                const valA = scoresA?.[key] ?? null;
                const valB = scoresB?.[key] ?? null;
                const aWins = valA !== null && valB !== null && valA > valB;
                const bWins = valA !== null && valB !== null && valB > valA;

                return (
                  <tr key={key} className="border-b">
                    <td className="px-6 py-3 font-medium">{label}</td>
                    <td className={`px-6 py-3 text-center text-lg ${aWins ? "text-green-600 font-bold" : ""}`}>
                      {valA !== null ? valA.toFixed(1) : "—"}
                    </td>
                    <td className={`px-6 py-3 text-center text-lg ${bWins ? "text-green-600 font-bold" : ""}`}>
                      {valB !== null ? valB.toFixed(1) : "—"}
                    </td>
                  </tr>
                );
              })}
              <tr>
                <td className="px-6 py-3 font-medium">National Rank</td>
                <td className="px-6 py-3 text-center">{scoresA?.national_rank ?? "—"}</td>
                <td className="px-6 py-3 text-center">{scoresB?.national_rank ?? "—"}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
