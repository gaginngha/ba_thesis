"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface TimeSeriesPoint {
  year: number;
  value: number | null;
}

interface TimeSeriesChartProps {
  title: string;
  data: TimeSeriesPoint[];
  color?: string;
}

export function TimeSeriesChart({
  title,
  data,
  color = "#0f3460",
}: TimeSeriesChartProps) {
  const chartData = data
    .filter((d) => d.value !== null)
    .map((d) => ({ year: d.year, value: d.value }));

  if (chartData.length === 0) {
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
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="year"
            tick={{ fontSize: 12 }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickLine={false}
            tickFormatter={(v) => v.toLocaleString("de-CH")}
          />
          <Tooltip
            formatter={(value: number) => [
              value.toLocaleString("de-CH", { maximumFractionDigits: 1 }),
              title,
            ]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
