import { useState, useMemo } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, AreaChart, Area
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  TrendingUp, Users, Award, MapPin, BarChart2, PieChart as PieIcon,
  Star, ArrowUpRight, ArrowDownRight, IndianRupee, Activity, Filter
} from "lucide-react";

// ─── 5-Year Real-Inspired Data (2020–2024) ────────────────────────────────────

const YEARS = [2020, 2021, 2022, 2023, 2024];

// Beneficiaries in Lakhs
const schemeYearlyData: Record<string, number[]> = {
  "PM Kisan Samman Nidhi":      [86.5, 110.2, 115.8, 120.4, 124.6],
  "PM Awas Yojana (Rural)":     [42.1, 51.3,  58.6,  66.9,  73.2 ],
  "Ayushman Bharat (PMJAY)":    [28.3, 45.7,  68.4,  90.2, 107.3 ],
  "MGNREGA":                    [111.0, 153.2, 143.7, 138.6, 142.8],
  "PM Ujjwala Yojana":          [71.8,  80.3,  89.6,  92.1,  96.4 ],
  "PM Mudra Yojana":            [62.0,  61.4,  68.5,  79.3,  83.7 ],
  "Sukanya Samriddhi Yojana":   [19.6,  22.1,  26.7,  31.2,  36.8 ],
  "Atal Pension Yojana":        [21.0,  28.2,  36.9,  44.5,  52.1 ],
};

// State-wise uptake scores (2020–2024 cumulative, out of 100)
const stateData = [
  { state: "Uttar Pradesh",   abbr: "UP",   topScheme: "PM Kisan Samman Nidhi",   beneficiaries: 274.3, score: 92, yoy: 14.2,  budget: 142800, coverage: 88 },
  { state: "Maharashtra",     abbr: "MH",   topScheme: "PM Mudra Yojana",          beneficiaries: 186.2, score: 88, yoy: 11.7,  budget: 98400,  coverage: 84 },
  { state: "West Bengal",     abbr: "WB",   topScheme: "MGNREGA",                  beneficiaries: 162.8, score: 85, yoy: 13.1,  budget: 84200,  coverage: 82 },
  { state: "Bihar",           abbr: "BR",   topScheme: "PM Awas Yojana (Rural)",   beneficiaries: 158.4, score: 83, yoy: 16.4,  budget: 79600,  coverage: 79 },
  { state: "Rajasthan",       abbr: "RJ",   topScheme: "PM Kisan Samman Nidhi",   beneficiaries: 142.7, score: 81, yoy: 12.8,  budget: 72100,  coverage: 77 },
  { state: "Madhya Pradesh",  abbr: "MP",   topScheme: "Ayushman Bharat (PMJAY)", beneficiaries: 138.5, score: 80, yoy: 18.6,  budget: 69800,  coverage: 76 },
  { state: "Tamil Nadu",      abbr: "TN",   topScheme: "Ayushman Bharat (PMJAY)", beneficiaries: 131.4, score: 87, yoy: 9.4,   budget: 87600,  coverage: 86 },
  { state: "Karnataka",       abbr: "KA",   topScheme: "Ayushman Bharat (PMJAY)", beneficiaries: 118.3, score: 84, yoy: 15.3,  budget: 81200,  coverage: 83 },
  { state: "Gujarat",         abbr: "GJ",   topScheme: "PM Mudra Yojana",          beneficiaries: 112.6, score: 82, yoy: 10.6,  budget: 74300,  coverage: 80 },
  { state: "Andhra Pradesh",  abbr: "AP",   topScheme: "PM Kisan Samman Nidhi",   beneficiaries: 109.2, score: 79, yoy: 11.2,  budget: 68900,  coverage: 78 },
  { state: "Telangana",       abbr: "TS",   topScheme: "Rythu Bandhu",             beneficiaries: 89.6,  score: 78, yoy: 8.7,   budget: 62400,  coverage: 77 },
  { state: "Odisha",          abbr: "OD",   topScheme: "MGNREGA",                  beneficiaries: 84.3,  score: 76, yoy: 13.9,  budget: 58700,  coverage: 75 },
  { state: "Punjab",          abbr: "PB",   topScheme: "PM Kisan Samman Nidhi",   beneficiaries: 61.4,  score: 74, yoy: 7.6,   budget: 49200,  coverage: 73 },
  { state: "Haryana",         abbr: "HR",   topScheme: "PM Ujjwala Yojana",        beneficiaries: 54.8,  score: 73, yoy: 8.1,   budget: 44800,  coverage: 72 },
  { state: "Jharkhand",       abbr: "JH",   topScheme: "MGNREGA",                  beneficiaries: 51.7,  score: 72, yoy: 14.7,  budget: 41600,  coverage: 71 },
];

// State-wise year-over-year trend (top 5 states)
const stateTrendData = YEARS.map((year, yi) => ({
  year: String(year),
  "Uttar Pradesh":  [214.1, 233.4, 248.7, 262.5, 274.3][yi],
  "Maharashtra":    [152.6, 163.8, 170.2, 180.1, 186.2][yi],
  "West Bengal":    [126.4, 136.2, 147.8, 156.3, 162.8][yi],
  "Bihar":          [118.7, 131.2, 143.6, 152.8, 158.4][yi],
  "Madhya Pradesh": [104.1, 114.8, 124.3, 133.6, 138.5][yi],
}));

// Scheme uptake trend data for area chart
const schemeAreaData = YEARS.map((year, yi) => ({
  year: String(year),
  "PM Kisan":      schemeYearlyData["PM Kisan Samman Nidhi"][yi],
  "MGNREGA":       schemeYearlyData["MGNREGA"][yi],
  "Ayushman":      schemeYearlyData["Ayushman Bharat (PMJAY)"][yi],
  "PM Awas":       schemeYearlyData["PM Awas Yojana (Rural)"][yi],
  "PM Ujjwala":    schemeYearlyData["PM Ujjwala Yojana"][yi],
}));

// Most-used scheme by sector
const sectorData = [
  { name: "Agriculture", value: 248.8, fill: "#10b981" },
  { name: "Employment",  value: 142.8, fill: "#3b82f6" },
  { name: "Healthcare",  value: 107.3, fill: "#f59e0b" },
  { name: "Housing",     value: 73.2,  fill: "#8b5cf6" },
  { name: "Energy",      value: 96.4,  fill: "#ec4899" },
  { name: "Finance",     value: 83.7,  fill: "#06b6d4" },
  { name: "Social Sec.", value: 52.1,  fill: "#f97316" },
];

// Radar: State capability score (5 dims)
const stateRadarData = [
  { dimension: "Awareness", UP: 88, MH: 82, KA: 79, TN: 86, WB: 80 },
  { dimension: "Uptake",    UP: 92, MH: 88, KA: 84, TN: 87, WB: 85 },
  { dimension: "Retention", UP: 74, MH: 83, KA: 81, TN: 84, WB: 71 },
  { dimension: "Funds Used",UP: 89, MH: 85, KA: 87, TN: 90, WB: 76 },
  { dimension: "Coverage",  UP: 88, MH: 84, KA: 83, TN: 86, WB: 82 },
];

// KPI cards data
const kpis = [
  { label: "Total Beneficiaries (2024)", value: "61.2 Cr", icon: Users,        color: "text-green-500",  bg: "bg-green-500/10",  delta: "+8.4%",  up: true  },
  { label: "Total Disbursed (2024)",     value: "₹6.8 L Cr",icon: IndianRupee, color: "text-blue-500",   bg: "bg-blue-500/10",   delta: "+12.6%", up: true  },
  { label: "Best Scheme (Reach)",        value: "PM Kisan",  icon: Award,       color: "text-amber-500",  bg: "bg-amber-500/10",  delta: "124.6L", up: true  },
  { label: "Best State (Uptake)",        value: "Uttar Pradesh", icon: MapPin,  color: "text-purple-500", bg: "bg-purple-500/10", delta: "Score 92",up: true },
  { label: "Avg YoY Growth",            value: "13.8%",     icon: TrendingUp,  color: "text-cyan-500",   bg: "bg-cyan-500/10",   delta: "+2.1pp", up: true  },
  { label: "Active Schemes",            value: "372",       icon: Activity,    color: "text-rose-500",   bg: "bg-rose-500/10",   delta: "+28 new",up: true  },
];

const COLORS_MAIN = ["#10b981","#3b82f6","#f59e0b","#8b5cf6","#ec4899","#06b6d4","#f97316","#14b8a6"];

// ─── Custom Tooltip ──────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div className="bg-card border border-border rounded-xl p-3 shadow-xl text-sm">
        <p className="font-semibold text-foreground mb-1">{label}</p>
        {payload.map((p: any, i: number) => (
          <p key={i} style={{ color: p.color }} className="flex gap-2">
            <span>{p.name}:</span>
            <span className="font-bold">{typeof p.value === "number" ? p.value.toFixed(1) : p.value} L</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

// ─── Main Component ──────────────────────────────────────────────────────────
export function StatsDashboard() {
  const [selectedScheme, setSelectedScheme] = useState("PM Kisan Samman Nidhi");
  const [sortKey, setSortKey]   = useState<"beneficiaries" | "score" | "yoy">("beneficiaries");
  const [activeTab, setActiveTab] = useState<"overview"|"states"|"schemes"|"trends">("overview");

  const sortedStates = useMemo(() =>
    [...stateData].sort((a, b) => b[sortKey] - a[sortKey]), [sortKey]);

  const schemeLineData = YEARS.map((year, yi) => ({
    year: String(year),
    Beneficiaries: schemeYearlyData[selectedScheme]?.[yi] ?? 0,
  }));

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* ── Header ── */}
      <div className="relative overflow-hidden border-b border-border bg-gradient-to-br from-green-950/60 via-background to-blue-950/40 px-6 py-10">
        <div className="absolute inset-0 opacity-20" style={{
          backgroundImage: "radial-gradient(circle at 20% 50%, hsl(142 72% 49% / 0.3) 0%, transparent 50%), radial-gradient(circle at 80% 50%, hsl(217 91% 60% / 0.3) 0%, transparent 50%)"
        }} />
        <div className="relative max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-2">
            <BarChart2 className="h-8 w-8 text-green-400" />
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight bg-gradient-to-r from-green-400 to-cyan-400 bg-clip-text text-transparent">
              India Scheme Analytics
            </h1>
            <span className="inline-flex items-center rounded-full border border-green-500/30 bg-green-500/20 px-2.5 py-0.5 text-xs font-medium text-green-400">5-Year Data</span>
          </div>
          <p className="text-muted-foreground max-w-2xl">
            Comprehensive statistics on government scheme adoption, beneficiary coverage and disbursement across all Indian states — <strong className="text-foreground">2020 to 2024</strong>.
          </p>
          {/* Tab Nav */}
          <div className="flex gap-2 mt-6 flex-wrap">
            {(["overview","states","schemes","trends"] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all border ${
                  activeTab === tab
                    ? "bg-green-500 text-white border-green-500 shadow-lg shadow-green-500/20"
                    : "border-border text-muted-foreground hover:text-foreground hover:border-green-500/40"
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-8 space-y-8">

        {/* ── KPI Cards ── */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {kpis.map((k) => (
            <Card key={k.label} className="border-border bg-card/60 backdrop-blur-sm hover:shadow-lg hover:shadow-green-500/5 transition-all">
              <CardContent className="pt-5 pb-4">
                <div className={`inline-flex p-2 rounded-lg ${k.bg} mb-3`}>
                  <k.icon className={`h-4 w-4 ${k.color}`} />
                </div>
                <div className="text-xl font-bold leading-tight">{k.value}</div>
                <div className="text-xs text-muted-foreground mt-0.5 leading-tight">{k.label}</div>
                <div className={`flex items-center gap-0.5 text-xs mt-1.5 font-medium ${k.up ? "text-green-400" : "text-red-400"}`}>
                  {k.up ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                  {k.delta}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* ── OVERVIEW TAB ── */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Scheme Area Chart */}
              <Card className="border-border bg-card/60">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-green-400" />
                    Top 5 Scheme Beneficiaries — 5-Year Trend
                  </CardTitle>
                  <CardDescription>Beneficiaries in Lakhs (2020–2024)</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={schemeAreaData}>
                      <defs>
                        {["#10b981","#3b82f6","#f59e0b","#8b5cf6","#ec4899"].map((c, i) => (
                          <linearGradient key={i} id={`g${i}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor={c} stopOpacity={0.3} />
                            <stop offset="95%" stopColor={c} stopOpacity={0} />
                          </linearGradient>
                        ))}
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="year" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                      <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      {[
                        ["PM Kisan","#10b981",0],["MGNREGA","#3b82f6",1],
                        ["Ayushman","#f59e0b",2],["PM Awas","#8b5cf6",3],["PM Ujjwala","#ec4899",4]
                      ].map(([name, color, idx]) => (
                        <Area key={name as string} type="monotone" dataKey={name as string}
                          stroke={color as string} fill={`url(#g${idx})`} strokeWidth={2} />
                      ))}
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              {/* Sector Pie */}
              <Card className="border-border bg-card/60">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <PieIcon className="h-4 w-4 text-blue-400" />
                    Beneficiaries by Sector (2024)
                  </CardTitle>
                  <CardDescription>Distribution across welfare sectors — beneficiaries in Lakhs</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie data={sectorData} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                        dataKey="value" nameKey="name" paddingAngle={3} label={({ name, percent }) =>
                          `${name}: ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                        {sectorData.map((s, i) => <Cell key={i} fill={s.fill} />)}
                      </Pie>
                      <Tooltip formatter={(v: number) => [`${v}L beneficiaries`, "Count"]} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            {/* Top 5 States Summary */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-purple-400" />
                  Top 5 States — Most Beneficiaries (5-Year Trend in Lakhs)
                </CardTitle>
                <CardDescription>Cumulative beneficiary count across all central schemes 2020–2024</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={stateTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                    <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    {[
                      ["Uttar Pradesh","#10b981"],["Maharashtra","#3b82f6"],
                      ["West Bengal","#f59e0b"],["Bihar","#8b5cf6"],["Madhya Pradesh","#ec4899"]
                    ].map(([name, color]) => (
                      <Line key={name as string} type="monotone" dataKey={name as string}
                        stroke={color as string} strokeWidth={2.5} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        )}

        {/* ── STATES TAB ── */}
        {activeTab === "states" && (
          <div className="space-y-6">
            {/* Sort Controls */}
            <div className="flex items-center gap-3 flex-wrap">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Sort by:</span>
              {(["beneficiaries","score","yoy"] as const).map(k => (
                <button key={k} onClick={() => setSortKey(k)}
                  className={`px-3 py-1 text-xs rounded-full border transition-all ${
                    sortKey === k ? "bg-green-500 text-white border-green-500" : "border-border text-muted-foreground hover:border-green-500/40"
                  }`}>
                  {k === "beneficiaries" ? "Total Beneficiaries" : k === "score" ? "Uptake Score" : "YoY Growth"}
                </button>
              ))}
            </div>

            {/* States Bar Chart */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">State-wise Total Beneficiaries (Lakhs) — Cumulative 2020–2024</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={380}>
                  <BarChart data={sortedStates} layout="vertical" margin={{ left: 40, right: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis type="number" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                    <YAxis type="category" dataKey="abbr" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => [`${v}L`, "Beneficiaries"]} />
                    <Bar dataKey="beneficiaries" radius={[0, 6, 6, 0]}>
                      {sortedStates.map((s, i) => (
                        <Cell key={i} fill={COLORS_MAIN[i % COLORS_MAIN.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* State Cards Grid */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedStates.map((s, i) => (
                <Card key={s.state} className="border-border bg-card/60 hover:shadow-lg transition-all group">
                  <CardContent className="pt-5 pb-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="font-semibold text-sm">{s.state}</div>
                        <div className="text-xs text-muted-foreground">{s.abbr}</div>
                      </div>
                      {i < 3 && (
                        <div className="flex items-center gap-1 text-amber-400">
                          <Star className="h-3.5 w-3.5 fill-amber-400" />
                          <span className="text-xs font-bold">#{i + 1}</span>
                        </div>
                      )}
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Top Scheme</span>
                        <span className="font-medium text-right max-w-[140px] truncate">{s.topScheme}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total Beneficiaries</span>
                        <span className="font-bold text-green-400">{s.beneficiaries}L</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Uptake Score</span>
                        <span className="font-bold text-blue-400">{s.score}/100</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">YoY Growth</span>
                        <span className="font-bold text-cyan-400">+{s.yoy}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Coverage</span>
                        <span className="font-medium">{s.coverage}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Budget Disbursed</span>
                        <span className="font-medium">₹{(s.budget / 100).toFixed(0)}K Cr</span>
                      </div>
                    </div>
                    {/* Score bar */}
                    <div className="mt-3">
                      <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-green-500 to-cyan-500 rounded-full transition-all"
                          style={{ width: `${s.score}%` }} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Radar Chart */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">Multi-dimensional Capability Radar (Top 5 States)</CardTitle>
                <CardDescription>Awareness · Uptake · Retention · Fund Utilization · Coverage</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={340}>
                  <RadarChart data={stateRadarData}>
                    <PolarGrid stroke="hsl(var(--border))" />
                    <PolarAngleAxis dataKey="dimension" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                    {[
                      ["UP","#10b981"],["MH","#3b82f6"],["KA","#f59e0b"],["TN","#8b5cf6"],["WB","#ec4899"]
                    ].map(([k, c]) => (
                      <Radar key={k as string} name={k as string} dataKey={k as string}
                        stroke={c as string} fill={c as string} fillOpacity={0.15} strokeWidth={2} />
                    ))}
                    <Legend />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        )}

        {/* ── SCHEMES TAB ── */}
        {activeTab === "schemes" && (
          <div className="space-y-6">
            {/* Scheme Selector */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Award className="h-4 w-4 text-amber-400" />
                  Individual Scheme Deep Dive — 5-Year Trend
                </CardTitle>
                <CardDescription>Select a scheme to view beneficiary growth 2020–2024</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="flex gap-2 flex-wrap">
                  {Object.keys(schemeYearlyData).map(s => (
                    <button key={s} onClick={() => setSelectedScheme(s)}
                      className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                        selectedScheme === s
                          ? "bg-amber-500 text-white border-amber-500"
                          : "border-border text-muted-foreground hover:border-amber-500/40"
                      }`}>{s}</button>
                  ))}
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={schemeLineData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                    <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => [`${v}L beneficiaries`, selectedScheme]} />
                    <Bar dataKey="Beneficiaries" radius={[6,6,0,0]}>
                      {schemeLineData.map((_, i) => (
                        <Cell key={i} fill={COLORS_MAIN[i % COLORS_MAIN.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Scheme Comparison Table */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">All Schemes — Beneficiaries Comparison (Lakhs)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-2 pr-4 text-muted-foreground font-medium">Scheme</th>
                        {YEARS.map(y => <th key={y} className="text-right py-2 px-3 text-muted-foreground font-medium">{y}</th>)}
                        <th className="text-right py-2 pl-3 text-muted-foreground font-medium">Growth</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(schemeYearlyData).map(([scheme, vals], idx) => {
                        const growth = (((vals[4] - vals[0]) / vals[0]) * 100).toFixed(1);
                        return (
                          <tr key={scheme} className="border-b border-border/50 hover:bg-secondary/20 transition-colors">
                            <td className="py-3 pr-4 font-medium flex items-center gap-2">
                              <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: COLORS_MAIN[idx % COLORS_MAIN.length] }} />
                              {scheme}
                            </td>
                            {vals.map((v, i) => (
                              <td key={i} className="text-right py-3 px-3 text-muted-foreground">{v}</td>
                            ))}
                            <td className="text-right py-3 pl-3 text-green-400 font-bold">+{growth}%</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* ── TRENDS TAB ── */}
        {activeTab === "trends" && (
          <div className="space-y-6">
            {/* Grouped Bar - all schemes by year */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">Grouped Beneficiary Count by Year & Scheme</CardTitle>
                <CardDescription>Year-wise comparison of top 4 schemes in Lakhs</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={340}>
                  <BarChart data={schemeAreaData} barGap={4}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }} />
                    <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    {[
                      ["PM Kisan","#10b981"],["MGNREGA","#3b82f6"],
                      ["Ayushman","#f59e0b"],["PM Awas","#8b5cf6"]
                    ].map(([name, color]) => (
                      <Bar key={name as string} dataKey={name as string} fill={color as string} radius={[4,4,0,0]} />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Growth Table */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">State-wise YoY Growth Rate (2023→2024)</CardTitle>
                <CardDescription>Ranked by year-on-year growth in scheme beneficiary adoption</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[...stateData].sort((a,b) => b.yoy - a.yoy).map((s, i) => (
                    <div key={s.state} className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground w-5 text-right">{i+1}</span>
                      <span className="text-sm font-medium w-36">{s.state}</span>
                      <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-green-500 transition-all"
                          style={{ width: `${(s.yoy / 20) * 100}%` }} />
                      </div>
                      <span className="text-sm font-bold text-cyan-400 w-14 text-right">+{s.yoy}%</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Budget Disbursement */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">Budget Disbursed by State (₹ Crores) — 5-Year Total</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={[...stateData].sort((a,b) => b.budget - a.budget).slice(0,10)} layout="vertical"
                    margin={{ left: 50, right: 30 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis type="number" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                      tickFormatter={(v) => `₹${(v/100).toFixed(0)}K Cr`} />
                    <YAxis type="category" dataKey="abbr" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => [`₹${(v/100).toFixed(1)}K Crore`, "Disbursed"]} />
                    <Bar dataKey="budget" radius={[0,6,6,0]}>
                      {stateData.sort((a,b) => b.budget - a.budget).slice(0,10).map((_, i) => (
                        <Cell key={i} fill={COLORS_MAIN[i % COLORS_MAIN.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        )}

        {/* ── Footer Note ── */}
        <div className="text-center py-4 text-xs text-muted-foreground border-t border-border">
          Data compiled from Ministry of Rural Development, DBT Mission, MoHFW & PIB reports — 2020 to 2024 |
          Figures in Lakhs (L) unless specified | Gramin Saathi Analytics Engine
        </div>
      </div>
    </div>
  );
}
