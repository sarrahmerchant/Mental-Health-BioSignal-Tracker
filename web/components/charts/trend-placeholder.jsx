"use client";

import {
  Area,
  AreaChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/** Static ticks so Recharts is wired — not patient data. */
const DATA = [
  { label: "Mon", value: 12 },
  { label: "Tue", value: 18 },
  { label: "Wed", value: 15 },
  { label: "Thu", value: 22 },
  { label: "Fri", value: 19 },
];

/** Fixed pixel size avoids ResponsiveContainer SSR/layout edge cases in the app shell. */
const CHART_W = 520;
const CHART_H = 200;

export function TrendPlaceholder() {
  return (
    <div className="flex w-full justify-center overflow-x-auto">
      <AreaChart
        width={CHART_W}
        height={CHART_H}
        data={DATA}
        margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
      >
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-chart-2)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--color-chart-2)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          className="text-xs"
          tick={{ fill: "var(--color-muted-foreground)" }}
        />
        <YAxis hide domain={["dataMin - 2", "dataMax + 2"]} />
        <Tooltip
          contentStyle={{
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--color-border)",
            background: "var(--color-card)",
          }}
          labelStyle={{ color: "var(--color-foreground)" }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="var(--color-chart-2)"
          fill="url(#trendFill)"
          strokeWidth={2}
        />
      </AreaChart>
    </div>
  );
}
