"use client";

import {
  Radar,
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface RadarDataPoint {
  dimension: string;
  value: number;
}

interface RadarChartProps {
  title: string;
  data: RadarDataPoint[];
  color?: string;
  maxValue?: number;
}

export function RadarChart({
  title,
  data,
  color = "#0f3460",
  maxValue = 100,
}: RadarChartProps) {
  if (data.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-sm font-medium text-gray-600 mb-4">{title}</h3>
        <p className="text-gray-400 text-center py-8">No data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="text-sm font-medium text-gray-600 mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={280}>
        <RechartsRadar data={data} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid stroke="#e5e7eb" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 12, fill: "#6b7280" }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, maxValue]}
            tick={{ fontSize: 10 }}
            tickCount={5}
          />
          <Tooltip
            formatter={(value: number) => [value.toFixed(1), "Score"]}
          />
          <Radar
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={0.2}
            strokeWidth={2}
          />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  );
}
