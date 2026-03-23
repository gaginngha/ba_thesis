"use client";

import { useState, useEffect } from "react";
import { api, Municipality } from "@/lib/api";
import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const AVAILABLE_METRICS = [
  { key: "net_debt_per_capita", label: "Net Debt per Capita", color: "#ef4444" },
  { key: "revenue_per_capita", label: "Revenue per Capita", color: "#22c55e" },
  { key: "self_financing_ratio", label: "Self-Financing Ratio", color: "#3b82f6" },
  { key: "population_total", label: "Population", color: "#8b5cf6" },
  { key: "population_growth_rate", label: "Population Growth Rate", color: "#06b6d4" },
  { key: "composite_score", label: "Composite Score", color: "#f59e0b" },
];

interface TrendResult {
  direction: string;
  slope: number;
  r_squared: number;
  p_value: number;
  confidence: number;
}

interface ForecastPoint {
  year: number;
  predicted_value: number;
  confidence: number;
}

interface AnomalyPoint {
  year: number;
  value: number;
}

interface ForecastResponse {
  metric: string;
  municipality_bfs: number;
  historical: { year: number; value: number | null }[];
  trend: TrendResult;
  forecast: ForecastPoint[];
  anomalies: AnomalyPoint[];
}

export default function TrendsPage() {
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<Municipality[]>([]);
  const [selected, setSelected] = useState<Municipality | null>(null);
  const [metric, setMetric] = useState("net_debt_per_capita");
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSearch(query: string) {
    setSearch(query);
    if (query.length < 2) { setResults([]); return; }
    const r = await api.municipalities.list({ search: query, limit: "10" });
    setResults(r);
  }

  async function selectMunicipality(m: Municipality) {
    setSelected(m);
    setResults([]);
    setSearch(m.name);
    loadForecast(m.bfs_number, metric);
  }

  async function loadForecast(bfs: number, met: string) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/trends/${bfs}/forecast/${met}?forecast_years=5`);
      const data = await res.json();
      setForecastData(data);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  }

  useEffect(() => {
    if (selected) {
      loadForecast(selected.bfs_number, metric);
    }
  }, [metric]);

  // Combine historical + forecast into chart data
  const chartData = forecastData
    ? [
        ...forecastData.historical.map((h) => ({ year: h.year, value: h.value })),
        ...forecastData.forecast.map((f) => ({ year: f.year, value: f.predicted_value })),
      ]
    : [];

  const historicalData = forecastData?.historical.map((h) => ({ year: h.year, value: h.value })) || [];
  const forecastPoints = forecastData?.forecast.map((f) => ({ year: f.year, value: f.predicted_value })) || [];

  const trendColor =
    forecastData?.trend.direction === "improving" ? "text-green-600" :
    forecastData?.trend.direction === "declining" ? "text-red-600" :
    "text-yellow-600";

  const metricConfig = AVAILABLE_METRICS.find((m) => m.key === metric);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Trend Analysis & Forecasting</h1>

      {/* Search + Metric Selection */}
      <div className="flex gap-4 flex-wrap">
        <div className="relative flex-1 min-w-64">
          <input
            type="text"
            placeholder="Search municipality..."
            className="w-full px-4 py-2 rounded-lg border focus:border-swiss-accent outline-none"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
          />
          {results.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
              {results.map((m) => (
                <button
                  key={m.bfs_number}
                  className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b last:border-0 text-sm"
                  onClick={() => selectMunicipality(m)}
                >
                  {m.name} ({m.canton_abbreviation})
                </button>
              ))}
            </div>
          )}
        </div>

        <select
          className="px-3 py-2 border rounded-lg"
          value={metric}
          onChange={(e) => setMetric(e.target.value)}
        >
          {AVAILABLE_METRICS.map((m) => (
            <option key={m.key} value={m.key}>{m.label}</option>
          ))}
        </select>
      </div>

      {loading && <p className="text-gray-500">Loading trend data...</p>}

      {forecastData && selected && (
        <div className="space-y-6">
          {/* Trend Summary */}
          <div className="bg-white rounded-lg border p-6">
            <h2 className="text-xl font-semibold mb-4">
              {selected.name} — {metricConfig?.label}
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Trend Direction</div>
                <div className={`text-lg font-bold capitalize ${trendColor}`}>
                  {forecastData.trend.direction}
                </div>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Confidence</div>
                <div className="text-lg font-bold">
                  {forecastData.trend.confidence}%
                </div>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">R² (Fit)</div>
                <div className="text-lg font-bold">
                  {forecastData.trend.r_squared?.toFixed(3) ?? "—"}
                </div>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-500">Slope</div>
                <div className="text-lg font-bold">
                  {forecastData.trend.slope?.toFixed(2) ?? "—"} / year
                </div>
              </div>
            </div>

            {/* Historical Chart */}
            <TimeSeriesChart
              title={`Historical: ${metricConfig?.label}`}
              data={historicalData}
              color={metricConfig?.color || "#0f3460"}
            />
          </div>

          {/* Forecast */}
          {forecastPoints.length > 0 && (
            <div className="bg-white rounded-lg border p-6">
              <h3 className="text-lg font-semibold mb-4">Forecast (5 years)</h3>
              <TimeSeriesChart
                title={`Historical + Forecast: ${metricConfig?.label}`}
                data={chartData}
                color={metricConfig?.color || "#0f3460"}
              />
              <div className="mt-4">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Year</th>
                      <th className="px-4 py-2 text-right">Predicted Value</th>
                      <th className="px-4 py-2 text-right">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecastData.forecast.map((f) => (
                      <tr key={f.year} className="border-b">
                        <td className="px-4 py-2">{f.year}</td>
                        <td className="px-4 py-2 text-right font-mono">
                          {f.predicted_value.toLocaleString("de-CH", { maximumFractionDigits: 1 })}
                        </td>
                        <td className="px-4 py-2 text-right">{f.confidence}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Anomalies */}
          {forecastData.anomalies.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h3 className="font-semibold text-yellow-800 mb-2">Detected Anomalies</h3>
              <ul className="text-sm text-yellow-700 space-y-1">
                {forecastData.anomalies.map((a) => (
                  <li key={a.year}>
                    Year {a.year}: {a.value.toLocaleString("de-CH", { maximumFractionDigits: 1 })} (unusual value)
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {!selected && (
        <div className="bg-white rounded-lg border p-12 text-center text-gray-400">
          <p className="text-lg">Select a municipality to analyze trends</p>
          <p className="text-sm mt-2">
            Choose a metric and municipality to see historical data, trend direction, forecasts, and anomaly detection.
          </p>
        </div>
      )}
    </div>
  );
}
