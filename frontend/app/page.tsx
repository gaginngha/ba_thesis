"use client";

import { useState, useEffect } from "react";
import { api, Municipality } from "@/lib/api";
import Link from "next/link";

export default function HomePage() {
  const [search, setSearch] = useState("");
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (search.length < 2) {
      setMunicipalities([]);
      return;
    }
    setLoading(true);
    const timeout = setTimeout(() => {
      api.municipalities
        .list({ search, limit: "20" })
        .then(setMunicipalities)
        .catch(console.error)
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(timeout);
  }, [search]);

  return (
    <div className="space-y-8">
      <section className="text-center py-12">
        <h1 className="text-4xl font-bold mb-4">Swiss Municipality Analytics</h1>
        <p className="text-gray-600 text-lg max-w-2xl mx-auto">
          Multi-dimensional analytics platform for all Swiss municipalities.
          Financial health, demographics, tax attractiveness, and economic strength — in one place.
        </p>
      </section>

      {/* Search */}
      <section className="max-w-xl mx-auto">
        <input
          type="text"
          placeholder="Search municipalities (e.g., Zürich, Bern, Lugano)..."
          className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-swiss-accent focus:ring-2 focus:ring-swiss-accent/20 outline-none text-lg"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {loading && <p className="text-sm text-gray-500 mt-2">Searching...</p>}
        {municipalities.length > 0 && (
          <div className="mt-2 bg-white rounded-lg border shadow-lg max-h-96 overflow-y-auto">
            {municipalities.map((m) => (
              <Link
                key={m.bfs_number}
                href={`/dashboard/${m.bfs_number}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 border-b last:border-b-0"
              >
                <div>
                  <span className="font-medium">{m.name}</span>
                  <span className="text-gray-500 ml-2 text-sm">({m.canton_abbreviation})</span>
                </div>
                {m.population && (
                  <span className="text-sm text-gray-400">
                    {m.population.toLocaleString("de-CH")} Einw.
                  </span>
                )}
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Quick Stats */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
        <div className="bg-white rounded-lg border p-6 text-center">
          <div className="text-3xl font-bold text-swiss-accent">~2,131</div>
          <div className="text-gray-600 mt-1">Active Municipalities</div>
        </div>
        <div className="bg-white rounded-lg border p-6 text-center">
          <div className="text-3xl font-bold text-swiss-accent">26</div>
          <div className="text-gray-600 mt-1">Cantons</div>
        </div>
        <div className="bg-white rounded-lg border p-6 text-center">
          <div className="text-3xl font-bold text-swiss-accent">5</div>
          <div className="text-gray-600 mt-1">Analytics Dimensions</div>
        </div>
      </section>

      {/* Feature Cards */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        <Link href="/rankings" className="bg-white rounded-lg border p-6 hover:shadow-md transition">
          <h3 className="text-lg font-semibold mb-2">Rankings</h3>
          <p className="text-gray-600 text-sm">
            Explore composite scores and rankings across all municipalities. Filter by canton, peer group, or metric.
          </p>
        </Link>
        <Link href="/compare" className="bg-white rounded-lg border p-6 hover:shadow-md transition">
          <h3 className="text-lg font-semibold mb-2">Compare</h3>
          <p className="text-gray-600 text-sm">
            Side-by-side comparison of municipalities across all dimensions — financial, demographic, and economic.
          </p>
        </Link>
        <Link href="/map" className="bg-white rounded-lg border p-6 hover:shadow-md transition">
          <h3 className="text-lg font-semibold mb-2">Map Explorer</h3>
          <p className="text-gray-600 text-sm">
            Interactive choropleth map showing any metric across all Swiss municipalities with drill-down.
          </p>
        </Link>
        <div className="bg-white rounded-lg border p-6 opacity-60">
          <h3 className="text-lg font-semibold mb-2">Trend Analysis</h3>
          <p className="text-gray-600 text-sm">
            Time series analysis with trend detection, forecasting, and anomaly alerts for each municipality.
          </p>
        </div>
      </section>
    </div>
  );
}
