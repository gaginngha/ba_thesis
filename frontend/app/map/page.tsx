"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { api, Canton } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const METRICS = [
  { key: "composite_score", label: "Composite Score", colorScale: "green" },
  { key: "financial_health_score", label: "Financial Health", colorScale: "blue" },
  { key: "tax_attractiveness_score", label: "Tax Attractiveness", colorScale: "purple" },
  { key: "demographic_vitality_score", label: "Demographics", colorScale: "teal" },
  { key: "economic_strength_score", label: "Economy", colorScale: "orange" },
  { key: "net_debt_per_capita", label: "Net Debt p.c. (CHF)", colorScale: "red" },
  { key: "revenue_per_capita", label: "Revenue p.c. (CHF)", colorScale: "green" },
  { key: "population_total", label: "Population", colorScale: "blue" },
  { key: "population_growth_rate", label: "Pop. Growth Rate (%)", colorScale: "teal" },
  { key: "foreign_share", label: "Foreign Share (%)", colorScale: "purple" },
];

const COLOR_SCALES: Record<string, [string, string, string, string, string]> = {
  green:  ["#f7fcf5", "#c7e9c0", "#74c476", "#31a354", "#006d2c"],
  blue:   ["#f7fbff", "#c6dbef", "#6baed6", "#3182bd", "#08519c"],
  red:    ["#fff5f0", "#fcbba1", "#fb6a4a", "#de2d26", "#a50f15"],
  purple: ["#f2f0f7", "#cbc9e2", "#9e9ac8", "#756bb1", "#54278f"],
  orange: ["#fff5eb", "#fdd49e", "#fdae6b", "#f16913", "#8c2d04"],
  teal:   ["#f0f9e8", "#bae4bc", "#7bccc4", "#43a2ca", "#0868ac"],
};

interface TooltipData {
  name: string;
  canton: string;
  value: number | null;
  x: number;
  y: number;
}

export default function MapPage() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const [metric, setMetric] = useState("composite_score");
  const [year, setYear] = useState(2022);
  const [canton, setCanton] = useState("");
  const [cantons, setCantons] = useState<Canton[]>([]);
  const [loading, setLoading] = useState(true);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [stats, setStats] = useState<{ min: number; max: number; mean: number; count: number } | null>(null);

  useEffect(() => {
    api.municipalities.cantons().then(setCantons).catch(console.error);
  }, []);

  const loadMap = useCallback(async () => {
    if (!mapRef.current) return;

    setLoading(true);

    // Dynamic import to avoid SSR issues
    const maplibregl = (await import("maplibre-gl")).default;
    await import("maplibre-gl/dist/maplibre-gl.css");

    // Initialize map if not already done
    if (!mapInstanceRef.current) {
      mapInstanceRef.current = new maplibregl.Map({
        container: mapRef.current,
        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "&copy; OpenStreetMap contributors",
            },
          },
          layers: [
            {
              id: "osm-tiles",
              type: "raster",
              source: "osm",
              minzoom: 0,
              maxzoom: 19,
            },
          ],
        },
        center: [8.2275, 46.8182], // Center of Switzerland
        zoom: 7.5,
        maxBounds: [[5.5, 45.5], [11.0, 48.0]], // Switzerland bounds
      });

      mapInstanceRef.current.addControl(new maplibregl.NavigationControl(), "top-right");

      await new Promise<void>((resolve) => {
        mapInstanceRef.current.on("load", resolve);
      });
    }

    const map = mapInstanceRef.current;

    // Fetch choropleth data from API
    const params = new URLSearchParams({ year: year.toString() });
    if (canton) params.set("canton", canton);

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/geo/choropleth/${metric}?${params}`
      );
      const data = await response.json();

      setStats(data.metadata?.stats || null);

      // Remove existing source and layers
      if (map.getLayer("municipalities-fill")) map.removeLayer("municipalities-fill");
      if (map.getLayer("municipalities-outline")) map.removeLayer("municipalities-outline");
      if (map.getSource("municipalities")) map.removeSource("municipalities");

      if (data.features && data.features.length > 0) {
        map.addSource("municipalities", {
          type: "geojson",
          data: data,
        });

        // Build color expression based on metric value
        const metricConfig = METRICS.find((m) => m.key === metric);
        const scale = COLOR_SCALES[metricConfig?.colorScale || "green"];
        const s = data.metadata?.stats;

        let colorExpr: any = scale[2]; // Default mid color
        if (s && s.min !== s.max) {
          const range = s.max - s.min;
          const stops = [
            s.min,
            s.min + range * 0.25,
            s.min + range * 0.5,
            s.min + range * 0.75,
            s.max,
          ];
          colorExpr = [
            "interpolate",
            ["linear"],
            ["coalesce", ["get", "value"], s.mean],
            stops[0], scale[0],
            stops[1], scale[1],
            stops[2], scale[2],
            stops[3], scale[3],
            stops[4], scale[4],
          ];
        }

        map.addLayer({
          id: "municipalities-fill",
          type: "fill",
          source: "municipalities",
          paint: {
            "fill-color": colorExpr,
            "fill-opacity": 0.7,
          },
        });

        map.addLayer({
          id: "municipalities-outline",
          type: "line",
          source: "municipalities",
          paint: {
            "line-color": "#333",
            "line-width": 0.3,
          },
        });

        // Tooltip on hover
        map.on("mousemove", "municipalities-fill", (e: any) => {
          if (e.features && e.features.length > 0) {
            const f = e.features[0];
            map.getCanvas().style.cursor = "pointer";
            setTooltip({
              name: f.properties.name,
              canton: f.properties.canton,
              value: f.properties.value,
              x: e.point.x,
              y: e.point.y,
            });
          }
        });

        map.on("mouseleave", "municipalities-fill", () => {
          map.getCanvas().style.cursor = "";
          setTooltip(null);
        });

        // Click to navigate to dashboard
        map.on("click", "municipalities-fill", (e: any) => {
          if (e.features && e.features.length > 0) {
            const bfs = e.features[0].properties.bfs_number;
            window.location.href = `/dashboard/${bfs}`;
          }
        });
      }
    } catch (err) {
      console.error("Failed to load choropleth data:", err);
    }

    setLoading(false);
  }, [metric, year, canton]);

  useEffect(() => {
    loadMap();
  }, [loadMap]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  const metricConfig = METRICS.find((m) => m.key === metric);
  const scale = COLOR_SCALES[metricConfig?.colorScale || "green"];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Map Explorer</h1>
        {loading && <span className="text-sm text-gray-500">Loading map data...</span>}
      </div>

      {/* Controls */}
      <div className="flex gap-4 flex-wrap">
        <select
          className="px-3 py-2 border rounded-lg text-sm"
          value={metric}
          onChange={(e) => setMetric(e.target.value)}
        >
          {METRICS.map((m) => (
            <option key={m.key} value={m.key}>{m.label}</option>
          ))}
        </select>

        <select
          className="px-3 py-2 border rounded-lg text-sm"
          value={year}
          onChange={(e) => setYear(parseInt(e.target.value))}
        >
          {Array.from({ length: 10 }, (_, i) => 2023 - i).map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>

        <select
          className="px-3 py-2 border rounded-lg text-sm"
          value={canton}
          onChange={(e) => setCanton(e.target.value)}
        >
          <option value="">All Cantons</option>
          {cantons.map((c) => (
            <option key={c.abbreviation} value={c.abbreviation}>
              {c.name_de}
            </option>
          ))}
        </select>
      </div>

      {/* Map */}
      <div className="relative">
        <div ref={mapRef} className="w-full h-[600px] rounded-lg border" />

        {/* Tooltip */}
        {tooltip && (
          <div
            className="absolute pointer-events-none bg-white rounded-lg shadow-lg border px-3 py-2 text-sm z-10"
            style={{ left: tooltip.x + 10, top: tooltip.y - 40 }}
          >
            <div className="font-semibold">{tooltip.name} ({tooltip.canton})</div>
            <div className="text-gray-600">
              {metricConfig?.label}: {tooltip.value !== null ? tooltip.value.toLocaleString("de-CH", { maximumFractionDigits: 1 }) : "—"}
            </div>
          </div>
        )}

        {/* Legend */}
        {stats && (
          <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg border p-3 z-10">
            <div className="text-xs font-medium text-gray-600 mb-2">{metricConfig?.label}</div>
            <div className="flex items-center gap-1">
              {scale.map((color, i) => (
                <div key={i} className="w-8 h-4 rounded-sm" style={{ backgroundColor: color }} />
              ))}
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>{stats.min.toLocaleString("de-CH", { maximumFractionDigits: 0 })}</span>
              <span>{stats.max.toLocaleString("de-CH", { maximumFractionDigits: 0 })}</span>
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {stats.count} municipalities | Avg: {stats.mean.toLocaleString("de-CH", { maximumFractionDigits: 1 })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
