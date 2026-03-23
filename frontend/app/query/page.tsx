"use client";

import { useState } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface QueryResult {
  bfs_number: number;
  name: string;
  canton: string;
  population: number | null;
  metric: string;
  value: number | null;
  year: number;
}

interface QueryResponse {
  query: string;
  parsed: Record<string, any>;
  count: number;
  results: QueryResult[];
}

const EXAMPLE_QUERIES = [
  "Top 10 municipalities in Zürich by financial health",
  "Municipalities with population over 20000 sorted by tax attractiveness",
  "Best rural municipalities by composite score",
  "Bottom 5 municipalities by debt in Bern",
  "Top 20 most tax-attractive municipalities in Aargau",
  "Largest cities by population",
  "Municipalities with highest population growth in Zug",
];

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function executeQuery(q: string) {
    const queryText = q || query;
    if (queryText.length < 3) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/query/?q=${encodeURIComponent(queryText)}`
      );
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    }
    setLoading(false);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Natural Language Query</h1>
      <p className="text-gray-600">
        Ask questions about Swiss municipalities in plain English or German.
      </p>

      {/* Query Input */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="e.g., Top 10 municipalities in Zürich by financial health"
          className="flex-1 px-4 py-3 rounded-lg border focus:border-swiss-accent outline-none text-lg"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && executeQuery(query)}
        />
        <button
          onClick={() => executeQuery(query)}
          disabled={loading || query.length < 3}
          className="px-6 py-3 bg-swiss-accent text-white rounded-lg font-medium hover:bg-swiss-dark transition disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {/* Example Queries */}
      <div className="flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((eq) => (
          <button
            key={eq}
            className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition"
            onClick={() => { setQuery(eq); executeQuery(eq); }}
          >
            {eq}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {response && (
        <div className="space-y-4">
          {/* Parsed Query Info */}
          <div className="bg-gray-50 rounded-lg p-4 text-sm">
            <span className="font-medium">Interpreted as: </span>
            {response.parsed.canton && <span className="inline-block bg-blue-100 text-blue-800 px-2 py-0.5 rounded mr-2">Canton: {response.parsed.canton}</span>}
            <span className="inline-block bg-green-100 text-green-800 px-2 py-0.5 rounded mr-2">Metric: {response.parsed.sort_metric}</span>
            <span className="inline-block bg-purple-100 text-purple-800 px-2 py-0.5 rounded mr-2">Order: {response.parsed.sort_order}</span>
            <span className="inline-block bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded mr-2">Limit: {response.parsed.limit}</span>
            {response.parsed.peer_group && <span className="inline-block bg-orange-100 text-orange-800 px-2 py-0.5 rounded mr-2">Peer Group: {response.parsed.peer_group}</span>}
            {response.parsed.population_min && <span className="inline-block bg-teal-100 text-teal-800 px-2 py-0.5 rounded mr-2">Pop &gt; {response.parsed.population_min.toLocaleString()}</span>}
          </div>

          <div className="text-sm text-gray-500">{response.count} results</div>

          {/* Results Table */}
          <div className="bg-white rounded-lg border overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left">#</th>
                  <th className="px-4 py-3 text-left">Municipality</th>
                  <th className="px-4 py-3 text-left">Canton</th>
                  <th className="px-4 py-3 text-right">Population</th>
                  <th className="px-4 py-3 text-right">{response.parsed.sort_metric}</th>
                  <th className="px-4 py-3 text-right">Year</th>
                </tr>
              </thead>
              <tbody>
                {response.results.map((r, i) => (
                  <tr key={r.bfs_number} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/dashboard/${r.bfs_number}`}
                        className="text-swiss-accent hover:underline font-medium"
                      >
                        {r.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{r.canton}</td>
                    <td className="px-4 py-3 text-right font-mono">
                      {r.population?.toLocaleString("de-CH") ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold">
                      {r.value !== null ? r.value.toLocaleString("de-CH", { maximumFractionDigits: 1 }) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-500">{r.year}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!response && !loading && (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          <p className="text-lg">Type a question above or click an example</p>
          <p className="text-sm mt-2">
            Supports English and German — canton names, metrics, population filters, peer groups, and more.
          </p>
        </div>
      )}
    </div>
  );
}
