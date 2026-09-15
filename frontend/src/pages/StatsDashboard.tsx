import { useState, useMemo } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, AreaChart, Area, ScatterChart, Scatter, ZAxis
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  TrendingUp, Users, Award, MapPin, BarChart2, PieChart as PieIcon,
  Star, ArrowUpRight, IndianRupee, Activity, Filter, Search, ChevronUp, ChevronDown, Globe
} from "lucide-react";

// ─── ALL 36 STATES & UTs — 5-Year Real-Inspired Data (2020–2024) ──────────────

const YEARS = [2020, 2021, 2022, 2023, 2024];
const COLORS = ["#10b981","#3b82f6","#f59e0b","#8b5cf6","#ec4899","#06b6d4","#f97316","#14b8a6","#84cc16","#a855f7","#ef4444","#0ea5e9"];

// Central + State-specific schemes (all unique schemes across India)
const ALL_SCHEMES = [
  "PM Kisan Samman Nidhi",
  "MGNREGA",
  "Ayushman Bharat (PMJAY)",
  "PM Awas Yojana (Rural)",
  "PM Ujjwala Yojana",
  "PM Mudra Yojana",
  "Sukanya Samriddhi Yojana",
  "Atal Pension Yojana",
  "PM Jan Dhan Yojana",
  "Rythu Bandhu (Telangana)",
  "Gruha Lakshmi (Karnataka)",
  "Kalia Yojana (Odisha)",
  "KALIA Scholarship (Odisha)",
  "Ladli Behna Yojana (MP)",
  "Kanyashree Prakalpa (WB)",
  "Mukhya Mantri Kisan Kalyan (MP)",
  "Mukhya Mantri Yuva Udyami (MP)",
  "Amma Vodi (Andhra Pradesh)",
  "YSR Rythu Bharosa (AP)",
  "Kusum Yojana",
  "Stand Up India",
  "PM SVANidhi",
  "PMEGP",
  "NSP (National Scholarship)",
];

// 5-Year national scheme data (beneficiaries in Lakhs)
const schemeNationalData: Record<string, number[]> = {
  "PM Kisan Samman Nidhi":     [86.5, 110.2, 115.8, 120.4, 124.6],
  "MGNREGA":                   [111.0, 153.2, 143.7, 138.6, 142.8],
  "Ayushman Bharat (PMJAY)":   [28.3, 45.7, 68.4, 90.2, 107.3],
  "PM Awas Yojana (Rural)":    [42.1, 51.3, 58.6, 66.9, 73.2],
  "PM Ujjwala Yojana":         [71.8, 80.3, 89.6, 92.1, 96.4],
  "PM Mudra Yojana":           [62.0, 61.4, 68.5, 79.3, 83.7],
  "Sukanya Samriddhi Yojana":  [19.6, 22.1, 26.7, 31.2, 36.8],
  "Atal Pension Yojana":       [21.0, 28.2, 36.9, 44.5, 52.1],
  "PM Jan Dhan Yojana":        [38.0, 41.3, 44.8, 50.2, 53.7],
};

// ── ALL 36 STATES & UTs with per-state top scheme + 5-year data ──────────────
const ALL_STATE_DATA = [
  // LARGE STATES
  { state: "Uttar Pradesh",       abbr: "UP",  region: "North",     topScheme: "PM Kisan Samman Nidhi",     topSchemeBeneficiaries: [48.2,53.1,57.4,60.8,63.2], beneficiaries: [214.1,233.4,248.7,262.5,274.3], score: 92, yoy: 14.2, budget: 142800, coverage: 88, pop: 2392,
    schemes: [
      { name: "PM Kisan Samman Nidhi", pct: 38 },
      { name: "MGNREGA", pct: 26 },
      { name: "PM Awas Yojana (Rural)", pct: 18 },
      { name: "Ayushman Bharat (PMJAY)", pct: 12 },
      { name: "PM Ujjwala Yojana", pct: 6 },
    ]},
  { state: "Maharashtra",         abbr: "MH",  region: "West",      topScheme: "PM Mudra Yojana",            topSchemeBeneficiaries: [18.1,19.4,21.2,23.8,25.6], beneficiaries: [152.6,163.8,170.2,180.1,186.2], score: 88, yoy: 11.7, budget: 98400,  coverage: 84, pop: 1238,
    schemes: [
      { name: "PM Mudra Yojana", pct: 32 },
      { name: "Ayushman Bharat (PMJAY)", pct: 24 },
      { name: "PM Kisan Samman Nidhi", pct: 20 },
      { name: "MGNREGA", pct: 14 },
      { name: "PM Awas Yojana (Rural)", pct: 10 },
    ]},
  { state: "West Bengal",         abbr: "WB",  region: "East",      topScheme: "MGNREGA",                    topSchemeBeneficiaries: [28.4,35.2,33.6,32.1,33.8], beneficiaries: [126.4,136.2,147.8,156.3,162.8], score: 85, yoy: 13.1, budget: 84200,  coverage: 82, pop: 1014,
    schemes: [
      { name: "MGNREGA", pct: 36 },
      { name: "Kanyashree Prakalpa (WB)", pct: 22 },
      { name: "PM Kisan Samman Nidhi", pct: 18 },
      { name: "Ayushman Bharat (PMJAY)", pct: 14 },
      { name: "PM Awas Yojana (Rural)", pct: 10 },
    ]},
  { state: "Bihar",               abbr: "BR",  region: "East",      topScheme: "PM Awas Yojana (Rural)",     topSchemeBeneficiaries: [14.2,16.8,19.4,22.1,24.3], beneficiaries: [118.7,131.2,143.6,152.8,158.4], score: 83, yoy: 16.4, budget: 79600,  coverage: 79, pop: 1284,
    schemes: [
      { name: "PM Awas Yojana (Rural)", pct: 34 },
      { name: "MGNREGA", pct: 26 },
      { name: "PM Kisan Samman Nidhi", pct: 22 },
      { name: "PM Ujjwala Yojana", pct: 10 },
      { name: "Ayushman Bharat (PMJAY)", pct: 8 },
    ]},
  { state: "Rajasthan",           abbr: "RJ",  region: "North",     topScheme: "PM Kisan Samman Nidhi",     topSchemeBeneficiaries: [22.1,26.3,28.4,30.1,31.8], beneficiaries: [118.4,127.6,133.8,139.4,142.7], score: 81, yoy: 12.8, budget: 72100,  coverage: 77, pop: 815,
    schemes: [
      { name: "PM Kisan Samman Nidhi", pct: 35 },
      { name: "MGNREGA", pct: 28 },
      { name: "Ayushman Bharat (PMJAY)", pct: 18 },
      { name: "PM Ujjwala Yojana", pct: 12 },
      { name: "PM Mudra Yojana", pct: 7 },
    ]},
  { state: "Madhya Pradesh",      abbr: "MP",  region: "Central",   topScheme: "Ladli Behna Yojana (MP)",    topSchemeBeneficiaries: [0,0,0,12.6,14.8],           beneficiaries: [104.1,114.8,124.3,133.6,138.5], score: 80, yoy: 18.6, budget: 69800,  coverage: 76, pop: 853,
    schemes: [
      { name: "Ladli Behna Yojana (MP)", pct: 28 },
      { name: "Ayushman Bharat (PMJAY)", pct: 24 },
      { name: "PM Kisan Samman Nidhi", pct: 22 },
      { name: "MGNREGA", pct: 18 },
      { name: "Mukhya Mantri Kisan Kalyan (MP)", pct: 8 },
    ]},
  { state: "Tamil Nadu",          abbr: "TN",  region: "South",     topScheme: "Ayushman Bharat (PMJAY)",   topSchemeBeneficiaries: [7.4,11.6,16.2,20.8,24.2],  beneficiaries: [108.6,114.8,121.4,127.6,131.4], score: 87, yoy: 9.4,  budget: 87600,  coverage: 86, pop: 772,
    schemes: [
      { name: "Ayushman Bharat (PMJAY)", pct: 34 },
      { name: "PM Kisan Samman Nidhi", pct: 22 },
      { name: "MGNREGA", pct: 18 },
      { name: "PM Mudra Yojana", pct: 16 },
      { name: "NSP (National Scholarship)", pct: 10 },
    ]},
  { state: "Karnataka",           abbr: "KA",  region: "South",     topScheme: "Gruha Lakshmi (Karnataka)",  topSchemeBeneficiaries: [0,0,0,6.2,8.4],             beneficiaries: [96.4,103.8,109.2,115.6,118.3],  score: 84, yoy: 15.3, budget: 81200,  coverage: 83, pop: 672,
    schemes: [
      { name: "Gruha Lakshmi (Karnataka)", pct: 26 },
      { name: "Ayushman Bharat (PMJAY)", pct: 28 },
      { name: "PM Kisan Samman Nidhi", pct: 22 },
      { name: "MGNREGA", pct: 14 },
      { name: "PM Mudra Yojana", pct: 10 },
    ]},
  { state: "Gujarat",             abbr: "GJ",  region: "West",      topScheme: "PM Mudra Yojana",            topSchemeBeneficiaries: [14.8,15.6,17.2,19.4,21.2], beneficiaries: [93.6,98.4,103.8,108.6,112.6],   score: 82, yoy: 10.6, budget: 74300,  coverage: 80, pop: 635,
    schemes: [
      { name: "PM Mudra Yojana", pct: 30 },
      { name: "PM Kisan Samman Nidhi", pct: 24 },
      { name: "Ayushman Bharat (PMJAY)", pct: 22 },
      { name: "Kusum Yojana", pct: 14 },
      { name: "Stand Up India", pct: 10 },
    ]},
  { state: "Andhra Pradesh",      abbr: "AP",  region: "South",     topScheme: "YSR Rythu Bharosa (AP)",     topSchemeBeneficiaries: [0,10.2,12.4,14.6,15.8],    beneficiaries: [90.4,96.8,101.6,106.4,109.2],   score: 79, yoy: 11.2, budget: 68900,  coverage: 78, pop: 534,
    schemes: [
      { name: "YSR Rythu Bharosa (AP)", pct: 30 },
      { name: "Amma Vodi (Andhra Pradesh)", pct: 24 },
      { name: "Ayushman Bharat (PMJAY)", pct: 20 },
      { name: "MGNREGA", pct: 16 },
      { name: "PM Kisan Samman Nidhi", pct: 10 },
    ]},
  { state: "Telangana",           abbr: "TS",  region: "South",     topScheme: "Rythu Bandhu (Telangana)",   topSchemeBeneficiaries: [9.8,12.2,14.4,15.8,16.6],  beneficiaries: [76.4,80.8,84.6,87.4,89.6],     score: 78, yoy: 8.7,  budget: 62400,  coverage: 77, pop: 385,
    schemes: [
      { name: "Rythu Bandhu (Telangana)", pct: 38 },
      { name: "Ayushman Bharat (PMJAY)", pct: 26 },
      { name: "MGNREGA", pct: 18 },
      { name: "PM Mudra Yojana", pct: 12 },
      { name: "PM Ujjwala Yojana", pct: 6 },
    ]},
  { state: "Odisha",              abbr: "OD",  region: "East",      topScheme: "Kalia Yojana (Odisha)",      topSchemeBeneficiaries: [8.6,10.4,11.8,13.2,14.6],  beneficiaries: [70.2,74.8,78.6,81.8,84.3],     score: 76, yoy: 13.9, budget: 58700,  coverage: 75, pop: 462,
    schemes: [
      { name: "Kalia Yojana (Odisha)", pct: 34 },
      { name: "MGNREGA", pct: 28 },
      { name: "PM Awas Yojana (Rural)", pct: 20 },
      { name: "Ayushman Bharat (PMJAY)", pct: 12 },
      { name: "PM Kisan Samman Nidhi", pct: 6 },
    ]},
  { state: "Punjab",              abbr: "PB",  region: "North",     topScheme: "PM Kisan Samman Nidhi",     topSchemeBeneficiaries: [9.2,10.4,11.6,12.4,13.1],  beneficiaries: [52.6,55.4,57.8,59.8,61.4],     score: 74, yoy: 7.6,  budget: 49200,  coverage: 73, pop: 299,
    schemes: [
      { name: "PM Kisan Samman Nidhi", pct: 40 },
      { name: "PM Mudra Yojana", pct: 22 },
      { name: "MGNREGA", pct: 16 },
      { name: "Ayushman Bharat (PMJAY)", pct: 14 },
      { name: "Atal Pension Yojana", pct: 8 },
    ]},
  { state: "Haryana",             abbr: "HR",  region: "North",     topScheme: "PM Ujjwala Yojana",          topSchemeBeneficiaries: [6.4,7.2,8.1,8.6,9.1],      beneficiaries: [46.8,49.2,51.4,53.2,54.8],     score: 73, yoy: 8.1,  budget: 44800,  coverage: 72, pop: 286,
    schemes: [
      { name: "PM Ujjwala Yojana", pct: 32 },
      { name: "PM Kisan Samman Nidhi", pct: 28 },
      { name: "Ayushman Bharat (PMJAY)", pct: 20 },
      { name: "PM Mudra Yojana", pct: 12 },
      { name: "Sukanya Samriddhi Yojana", pct: 8 },
    ]},
  { state: "Jharkhand",           abbr: "JH",  region: "East",      topScheme: "MGNREGA",                    topSchemeBeneficiaries: [12.4,16.2,15.6,14.8,15.4], beneficiaries: [43.4,45.8,48.2,50.2,51.7],     score: 72, yoy: 14.7, budget: 41600,  coverage: 71, pop: 392,
    schemes: [
      { name: "MGNREGA", pct: 38 },
      { name: "PM Awas Yojana (Rural)", pct: 26 },
      { name: "Ayushman Bharat (PMJAY)", pct: 18 },
      { name: "PM Kisan Samman Nidhi", pct: 12 },
      { name: "PM Ujjwala Yojana", pct: 6 },
    ]},
  { state: "Assam",               abbr: "AS",  region: "Northeast", topScheme: "MGNREGA",                    topSchemeBeneficiaries: [8.2,10.6,10.1,9.8,10.4],   beneficiaries: [36.2,39.4,42.6,44.8,47.2],     score: 70, yoy: 12.4, budget: 36400,  coverage: 68, pop: 355,
    schemes: [
      { name: "MGNREGA", pct: 34 },
      { name: "PM Awas Yojana (Rural)", pct: 24 },
      { name: "PM Ujjwala Yojana", pct: 18 },
      { name: "Ayushman Bharat (PMJAY)", pct: 14 },
      { name: "PM Kisan Samman Nidhi", pct: 10 },
    ]},
  { state: "Chhattisgarh",        abbr: "CG",  region: "Central",   topScheme: "MGNREGA",                    topSchemeBeneficiaries: [7.8,10.4,9.6,9.2,9.8],     beneficiaries: [31.4,34.6,37.2,39.4,41.8],     score: 71, yoy: 13.2, budget: 33800,  coverage: 70, pop: 293,
    schemes: [
      { name: "MGNREGA", pct: 36 },
      { name: "Ayushman Bharat (PMJAY)", pct: 24 },
      { name: "PM Awas Yojana (Rural)", pct: 20 },
      { name: "PM Kisan Samman Nidhi", pct: 14 },
      { name: "PM Ujjwala Yojana", pct: 6 },
    ]},
  { state: "Kerala",              abbr: "KL",  region: "South",     topScheme: "Ayushman Bharat (PMJAY)",   topSchemeBeneficiaries: [4.2,6.8,9.4,12.1,14.6],    beneficiaries: [28.6,31.2,33.8,36.4,38.6],     score: 89, yoy: 7.2,  budget: 42600,  coverage: 91, pop: 352,
    schemes: [
      { name: "Ayushman Bharat (PMJAY)", pct: 40 },
      { name: "PM Mudra Yojana", pct: 24 },
      { name: "PM Jan Dhan Yojana", pct: 18 },
      { name: "Sukanya Samriddhi Yojana", pct: 12 },
      { name: "NSP (National Scholarship)", pct: 6 },
    ]},
  { state: "Uttarakhand",         abbr: "UK",  region: "North",     topScheme: "PM Kisan Samman Nidhi",     topSchemeBeneficiaries: [3.8,4.6,5.1,5.6,6.0],      beneficiaries: [18.4,20.2,22.4,24.2,26.1],     score: 76, yoy: 9.8,  budget: 28400,  coverage: 75, pop: 114,
    schemes: [
      { name: "PM Kisan Samman Nidhi", pct: 34 },
      { name: "Ayushman Bharat (PMJAY)", pct: 26 },
      { name: "MGNREGA", pct: 22 },
      { name: "PM Ujjwala Yojana", pct: 12 },
      { name: "Kusum Yojana", pct: 6 },
    ]},
  { state: "Himachal Pradesh",    abbr: "HP",  region: "North",     topScheme: "PM Kisan Samman Nidhi",     topSchemeBeneficiaries: [2.1,2.6,2.9,3.2,3.4],      beneficiaries: [10.2,11.4,12.6,13.8,14.8],     score: 81, yoy: 8.4,  budget: 21600,  coverage: 82, pop: 74,
    schemes: [
      { name: "PM Kisan Samman Nidhi", pct: 38 },
      { name: "Ayushman Bharat (PMJAY)", pct: 28 },
      { name: "PM Mudra Yojana", pct: 18 },
      { name: "Atal Pension Yojana", pct: 10 },
      { name: "MGNREGA", pct: 6 },
    ]},
  { state: "Jammu & Kashmir",     abbr: "JK",  region: "North",     topScheme: "PM Awas Yojana (Rural)",     topSchemeBeneficiaries: [2.4,3.1,3.8,4.4,4.9],      beneficiaries: [10.8,12.4,14.2,16.1,17.6],     score: 73, yoy: 11.6, budget: 24800,  coverage: 71, pop: 135,
    schemes: [
      { name: "PM Awas Yojana (Rural)", pct: 36 },
      { name: "MGNREGA", pct: 28 },
      { name: "PM Kisan Samman Nidhi", pct: 18 },
      { name: "Ayushman Bharat (PMJAY)", pct: 12 },
      { name: "PM Ujjwala Yojana", pct: 6 },
    ]},
  { state: "Tripura",             abbr: "TR",  region: "Northeast", topScheme: "MGNREGA",                    topSchemeBeneficiaries: [2.8,3.6,3.4,3.2,3.4],      beneficiaries: [9.2,10.4,11.2,12.1,12.8],      score: 72, yoy: 10.8, budget: 18400,  coverage: 70, pop: 41,
    schemes: [
      { name: "MGNREGA", pct: 40 },
      { name: "PM Awas Yojana (Rural)", pct: 28 },
      { name: "Ayushman Bharat (PMJAY)", pct: 16 },
      { name: "PM Ujjwala Yojana", pct: 10 },
      { name: "PM Kisan Samman Nidhi", pct: 6 },
    ]},
  { state: "Meghalaya",           abbr: "ML",  region: "Northeast", topScheme: "MGNREGA",                    topSchemeBeneficiaries: [1.8,2.4,2.2,2.1,2.3],      beneficiaries: [7.4,8.2,9.1,9.8,10.4],         score: 67, yoy: 11.2, budget: 14800,  coverage: 66, pop: 34,
    schemes: [
      { name: "MGNREGA", pct: 42 },
      { name: "PM Awas Yojana (Rural)", pct: 26 },
      { name: "Ayushman Bharat (PMJAY)", pct: 18 },
      { name: "PM Ujjwala Yojana", pct: 8 },
      { name: "PM Kisan Samman Nidhi", pct: 6 },
    ]},
  { state: "Manipur",             abbr: "MN",  region: "Northeast", topScheme: "PM Awas Yojana (Rural)",     topSchemeBeneficiaries: [0.8,1.1,1.4,1.6,1.8],      beneficiaries: [4.6,5.2,6.1,6.8,7.4],          score: 66, yoy: 12.8, budget: 12600,  coverage: 64, pop: 31,
    schemes: [
      { name: "PM Awas Yojana (Rural)", pct: 36 },
      { name: "MGNREGA", pct: 30 },
      { name: "Ayushman Bharat (PMJAY)", pct: 18 },
      { name: "PM Ujjwala Yojana", pct: 10 },
      { name: "PM Kisan Samman Nidhi", pct: 6 },
    ]},
  { state: "Nagaland",            abbr: "NL",  region: "Northeast", topScheme: "MGNREGA",                    topSchemeBeneficiaries: [0.9,1.2,1.1,1.0,1.1],      beneficiaries: [3.8,4.4,5.1,5.6,6.1],          score: 64, yoy: 11.4, budget: 10800,  coverage: 62, pop: 21,
    schemes: [
      { name: "MGNREGA", pct: 38 },
      { name: "PM Awas Yojana (Rural)", pct: 28 },
      { name: "Ayushman Bharat (PMJAY)", pct: 18 },
      { name: "PM Ujjwala Yojana", pct: 10 },
      { name: "NSP (National Scholarship)", pct: 6 },
    ]},
  { state: "Arunachal Pradesh",   abbr: "AR",  region: "Northeast", topScheme: "PM Awas Yojana (Rural)",     topSchemeBeneficiaries: [0.6,0.8,1.0,1.2,1.4],      beneficiaries: [3.2,3.8,4.6,5.2,5.8],          score: 65, yoy: 13.6, budget: 9600,   coverage: 63, pop: 15,
    schemes: [
      { name: "PM Awas Yojana (Rural)", pct: 38 },
      { name: "MGNREGA", pct: 32 },
      { name: "Ayushman Bharat (PMJAY)", pct: 16 },
      { name: "PM Ujjwala Yojana", pct: 8 },
      { name: "PM Kisan Samman Nidhi", pct: 6 },
    ]},
  { state: "Mizoram",             abbr: "MZ",  region: "Northeast", topScheme: "MGNREGA",                    topSchemeBeneficiaries: [0.7,0.9,0.8,0.8,0.9],      beneficiaries: [3.0,3.5,4.1,4.6,5.0],          score: 68, yoy: 10.6, budget: 8400,   coverage: 67, pop: 12,
    schemes: [
      { name: "MGNREGA", pct: 36 },
      { name: "Ayushman Bharat (PMJAY)", pct: 28 },
      { name: "PM Awas Yojana (Rural)", pct: 18 },
      { name: "NSP (National Scholarship)", pct: 12 },
      { name: "PM Ujjwala Yojana", pct: 6 },
    ]},
  { state: "Sikkim",              abbr: "SK",  region: "Northeast", topScheme: "Ayushman Bharat (PMJAY)",   topSchemeBeneficiaries: [0.3,0.5,0.7,0.9,1.1],      beneficiaries: [1.8,2.2,2.7,3.1,3.5],          score: 74, yoy: 9.2,  budget: 6800,   coverage: 75, pop: 7,
    schemes: [
      { name: "Ayushman Bharat (PMJAY)", pct: 44 },
      { name: "MGNREGA", pct: 24 },
      { name: "PM Kisan Samman Nidhi", pct: 16 },
      { name: "Atal Pension Yojana", pct: 10 },
      { name: "NSP (National Scholarship)", pct: 6 },
    ]},
  // UNION TERRITORIES
  { state: "Delhi",               abbr: "DL",  region: "North",     topScheme: "Ayushman Bharat (PMJAY)",   topSchemeBeneficiaries: [1.8,2.6,3.4,4.2,5.1],      beneficiaries: [12.4,14.2,16.1,18.0,19.8],     score: 82, yoy: 8.6,  budget: 28600,  coverage: 80, pop: 190,
    schemes: [
      { name: "Ayushman Bharat (PMJAY)", pct: 38 },
      { name: "PM Mudra Yojana", pct: 26 },
      { name: "PM Jan Dhan Yojana", pct: 18 },
      { name: "PM SVANidhi", pct: 12 },
      { name: "Atal Pension Yojana", pct: 6 },
    ]},
  { state: "Goa",                 abbr: "GA",  region: "West",      topScheme: "Ayushman Bharat (PMJAY)",   topSchemeBeneficiaries: [0.4,0.6,0.9,1.1,1.4],      beneficiaries: [2.6,3.1,3.6,4.1,4.6],          score: 86, yoy: 6.8,  budget: 9800,   coverage: 87, pop: 15,
    schemes: [
      { name: "Ayushman Bharat (PMJAY)", pct: 42 },
      { name: "PM Mudra Yojana", pct: 26 },
      { name: "PM Jan Dhan Yojana", pct: 16 },
      { name: "Atal Pension Yojana", pct: 10 },
      { name: "Stand Up India", pct: 6 },
    ]},
  { state: "Chandigarh (UT)",     abbr: "CH",  region: "North",     topScheme: "Ayushman Bharat (PMJAY)",   topSchemeBeneficiaries: [0.2,0.3,0.4,0.5,0.6],      beneficiaries: [1.2,1.5,1.8,2.1,2.4],          score: 83, yoy: 7.4,  budget: 4800,   coverage: 84, pop: 11,
    schemes: [
      { name: "Ayushman Bharat (PMJAY)", pct: 40 },
      { name: "PM Mudra Yojana", pct: 26 },
      { name: "PM Jan Dhan Yojana", pct: 18 },
      { name: "Atal Pension Yojana", pct: 10 },
      { name: "Stand Up India", pct: 6 },
    ]},
  { state: "Puducherry",          abbr: "PY",  region: "South",     topScheme: "Ayushman Bharat (PMJAY)",   topSchemeBeneficiaries: [0.3,0.4,0.6,0.8,0.9],      beneficiaries: [1.6,1.9,2.3,2.7,3.0],          score: 80, yoy: 8.2,  budget: 5600,   coverage: 81, pop: 14,
    schemes: [
      { name: "Ayushman Bharat (PMJAY)", pct: 40 },
      { name: "PM Mudra Yojana", pct: 24 },
      { name: "PM Kisan Samman Nidhi", pct: 18 },
      { name: "MGNREGA", pct: 12 },
      { name: "PM Ujjwala Yojana", pct: 6 },
    ]},
  { state: "Ladakh (UT)",         abbr: "LA",  region: "North",     topScheme: "PM Awas Yojana (Rural)",     topSchemeBeneficiaries: [0.08,0.11,0.14,0.17,0.20], beneficiaries: [0.5,0.7,0.9,1.1,1.3],          score: 69, yoy: 14.2, budget: 2600,   coverage: 68, pop: 3,
    schemes: [
      { name: "PM Awas Yojana (Rural)", pct: 42 },
      { name: "MGNREGA", pct: 28 },
      { name: "Ayushman Bharat (PMJAY)", pct: 16 },
      { name: "PM Kisan Samman Nidhi", pct: 8 },
      { name: "PM Ujjwala Yojana", pct: 6 },
    ]},
  { state: "A&N Islands (UT)",    abbr: "AN",  region: "South",     topScheme: "PM Jan Dhan Yojana",         topSchemeBeneficiaries: [0.06,0.08,0.10,0.12,0.14], beneficiaries: [0.4,0.5,0.6,0.7,0.8],          score: 78, yoy: 7.8,  budget: 2200,   coverage: 79, pop: 4,
    schemes: [
      { name: "PM Jan Dhan Yojana", pct: 38 },
      { name: "Ayushman Bharat (PMJAY)", pct: 28 },
      { name: "PM Mudra Yojana", pct: 18 },
      { name: "Atal Pension Yojana", pct: 10 },
      { name: "PMEGP", pct: 6 },
    ]},
  { state: "D&NH & DD (UT)",      abbr: "DD",  region: "West",      topScheme: "PM Mudra Yojana",            topSchemeBeneficiaries: [0.12,0.15,0.18,0.21,0.24], beneficiaries: [0.7,0.9,1.1,1.3,1.5],          score: 76, yoy: 9.4,  budget: 3400,   coverage: 77, pop: 6,
    schemes: [
      { name: "PM Mudra Yojana", pct: 36 },
      { name: "Ayushman Bharat (PMJAY)", pct: 28 },
      { name: "PM Jan Dhan Yojana", pct: 18 },
      { name: "Stand Up India", pct: 12 },
      { name: "PMEGP", pct: 6 },
    ]},
  { state: "Lakshadweep (UT)",    abbr: "LD",  region: "South",     topScheme: "PM Jan Dhan Yojana",         topSchemeBeneficiaries: [0.01,0.01,0.02,0.02,0.02], beneficiaries: [0.08,0.10,0.12,0.14,0.16],     score: 71, yoy: 8.6,  budget: 800,    coverage: 72, pop: 0.7,
    schemes: [
      { name: "PM Jan Dhan Yojana", pct: 42 },
      { name: "Ayushman Bharat (PMJAY)", pct: 30 },
      { name: "PM Mudra Yojana", pct: 16 },
      { name: "Atal Pension Yojana", pct: 8 },
      { name: "PMEGP", pct: 4 },
    ]},
];

// Trend data: top 5 states only for line chart
const stateTrendData = YEARS.map((year, yi) => ({
  year: String(year),
  "Uttar Pradesh":  ALL_STATE_DATA[0].beneficiaries[yi],
  "Maharashtra":    ALL_STATE_DATA[1].beneficiaries[yi],
  "West Bengal":    ALL_STATE_DATA[2].beneficiaries[yi],
  "Bihar":          ALL_STATE_DATA[3].beneficiaries[yi],
  "Madhya Pradesh": ALL_STATE_DATA[5].beneficiaries[yi],
}));

// Scheme uptake area chart
const schemeAreaData = YEARS.map((year, yi) => ({
  year: String(year),
  "PM Kisan":    schemeNationalData["PM Kisan Samman Nidhi"][yi],
  "MGNREGA":     schemeNationalData["MGNREGA"][yi],
  "Ayushman":    schemeNationalData["Ayushman Bharat (PMJAY)"][yi],
  "PM Awas":     schemeNationalData["PM Awas Yojana (Rural)"][yi],
  "PM Ujjwala":  schemeNationalData["PM Ujjwala Yojana"][yi],
}));

// Sector pie
const sectorData = [
  { name: "Agriculture", value: 248.8, fill: "#10b981" },
  { name: "Employment",  value: 142.8, fill: "#3b82f6" },
  { name: "Healthcare",  value: 107.3, fill: "#f59e0b" },
  { name: "Housing",     value: 73.2,  fill: "#8b5cf6" },
  { name: "Energy",      value: 96.4,  fill: "#ec4899" },
  { name: "Finance",     value: 83.7,  fill: "#06b6d4" },
  { name: "Social Sec.", value: 52.1,  fill: "#f97316" },
];

const kpis = [
  { label: "Total Beneficiaries (2024)", value: "61.2 Cr",       icon: Users,        color: "text-green-500",  bg: "bg-green-500/10",  delta: "+8.4%",   up: true },
  { label: "Total Disbursed (2024)",     value: "₹6.8 L Cr",    icon: IndianRupee,  color: "text-blue-500",   bg: "bg-blue-500/10",   delta: "+12.6%",  up: true },
  { label: "Best Scheme (Reach)",        value: "PM Kisan",       icon: Award,        color: "text-amber-500",  bg: "bg-amber-500/10",  delta: "124.6L",  up: true },
  { label: "Best State (Uptake)",        value: "Uttar Pradesh",  icon: MapPin,       color: "text-purple-500", bg: "bg-purple-500/10", delta: "Score 92", up: true },
  { label: "Avg YoY Growth",            value: "11.8%",          icon: TrendingUp,   color: "text-cyan-500",   bg: "bg-cyan-500/10",   delta: "+1.9pp",  up: true },
  { label: "States & UTs Covered",      value: "36",             icon: Globe,        color: "text-rose-500",   bg: "bg-rose-500/10",   delta: "100%",    up: true },
];

const REGION_COLORS: Record<string, string> = {
  "North": "#3b82f6", "South": "#10b981", "East": "#f59e0b",
  "West": "#8b5cf6", "Central": "#ec4899", "Northeast": "#06b6d4",
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div className="bg-card border border-border rounded-xl p-3 shadow-xl text-sm max-w-xs">
        <p className="font-semibold text-foreground mb-1">{label}</p>
        {payload.map((p: any, i: number) => (
          <p key={i} style={{ color: p.color }} className="flex justify-between gap-4">
            <span className="truncate">{p.name}:</span>
            <span className="font-bold flex-shrink-0">{typeof p.value === "number" ? p.value.toFixed(1) : p.value} L</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

// ─── MAIN COMPONENT ─────────────────────────────────────────────────────────
export function StatsDashboard() {
  const [selectedScheme, setSelectedScheme] = useState("PM Kisan Samman Nidhi");
  const [sortKey, setSortKey]   = useState<"beneficiaries" | "score" | "yoy" | "coverage">("beneficiaries");
  const [sortDir, setSortDir]   = useState<"desc" | "asc">("desc");
  const [activeTab, setActiveTab] = useState<"overview" | "states" | "schemes" | "trends">("overview");
  const [regionFilter, setRegionFilter] = useState<string>("All");
  const [searchQ, setSearchQ]   = useState("");
  const [selectedState, setSelectedState] = useState<typeof ALL_STATE_DATA[0] | null>(null);

  const regions = ["All", "North", "South", "East", "West", "Central", "Northeast"];

  const filteredStates = useMemo(() => {
    let data = [...ALL_STATE_DATA];
    if (regionFilter !== "All") data = data.filter(s => s.region === regionFilter);
    if (searchQ.trim()) data = data.filter(s => s.state.toLowerCase().includes(searchQ.toLowerCase()));
    data.sort((a, b) => {
      const va = sortKey === "beneficiaries" ? a.beneficiaries[4] : a[sortKey];
      const vb = sortKey === "beneficiaries" ? b.beneficiaries[4] : b[sortKey];
      return sortDir === "desc" ? (vb as number) - (va as number) : (va as number) - (vb as number);
    });
    return data;
  }, [sortKey, sortDir, regionFilter, searchQ]);

  const schemeBarData = YEARS.map((year, yi) => ({
    year: String(year),
    Beneficiaries: schemeNationalData[selectedScheme]?.[yi] ?? 0,
  }));

  const handleSort = (key: typeof sortKey) => {
    if (sortKey === key) setSortDir(d => d === "desc" ? "asc" : "desc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const SortIcon = ({ k }: { k: string }) => sortKey === k
    ? (sortDir === "desc" ? <ChevronDown className="h-3 w-3 inline ml-0.5" /> : <ChevronUp className="h-3 w-3 inline ml-0.5" />)
    : null;

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* HEADER */}
      <div className="relative overflow-hidden border-b border-border bg-gradient-to-br from-green-950/60 via-background to-blue-950/40 px-6 py-10">
        <div className="absolute inset-0 opacity-20" style={{
          backgroundImage: "radial-gradient(circle at 20% 50%, hsl(142 72% 49% / 0.3) 0%, transparent 50%), radial-gradient(circle at 80% 50%, hsl(217 91% 60% / 0.3) 0%, transparent 50%)"
        }} />
        <div className="relative max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <BarChart2 className="h-8 w-8 text-green-400" />
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight bg-gradient-to-r from-green-400 to-cyan-400 bg-clip-text text-transparent">
              India Scheme Analytics
            </h1>
            <span className="inline-flex items-center rounded-full border border-green-500/30 bg-green-500/20 px-2.5 py-0.5 text-xs font-medium text-green-400">All 36 States & UTs</span>
            <span className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-2.5 py-0.5 text-xs font-medium text-blue-400">5-Year: 2020–2024</span>
          </div>
          <p className="text-muted-foreground max-w-2xl text-sm">
            Comprehensive scheme adoption, beneficiary coverage and budget utilisation across <strong className="text-foreground">all 28 states + 8 union territories</strong>. Each state shows its own most-used scheme(s).
          </p>
          <div className="flex gap-2 mt-6 flex-wrap">
            {(["overview","states","schemes","trends"] as const).map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all border ${
                  activeTab === tab
                    ? "bg-green-500 text-white border-green-500 shadow-lg shadow-green-500/20"
                    : "border-border text-muted-foreground hover:text-foreground hover:border-green-500/40"
                }`}>
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 md:px-6 py-8 space-y-8">

        {/* KPI CARDS */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {kpis.map((k) => (
            <Card key={k.label} className="border-border bg-card/60 backdrop-blur-sm hover:shadow-lg hover:shadow-green-500/5 transition-all">
              <CardContent className="pt-5 pb-4">
                <div className={`inline-flex p-2 rounded-lg ${k.bg} mb-3`}>
                  <k.icon className={`h-4 w-4 ${k.color}`} />
                </div>
                <div className="text-xl font-bold leading-tight">{k.value}</div>
                <div className="text-xs text-muted-foreground mt-0.5 leading-tight">{k.label}</div>
                <div className={`flex items-center gap-0.5 text-xs mt-1.5 font-medium text-green-400`}>
                  <ArrowUpRight className="h-3 w-3" />{k.delta}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* ── OVERVIEW ── */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="border-border bg-card/60">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-green-400" />
                    Top 5 Scheme Beneficiaries — 5-Year Trend (Lakhs)
                  </CardTitle>
                  <CardDescription>National beneficiary count 2020–2024</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={schemeAreaData}>
                      <defs>
                        {["#10b981","#3b82f6","#f59e0b","#8b5cf6","#ec4899"].map((c,i)=>(
                          <linearGradient key={i} id={`g${i}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={c} stopOpacity={0.3}/>
                            <stop offset="95%" stopColor={c} stopOpacity={0}/>
                          </linearGradient>
                        ))}
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="year" tick={{ fill:"hsl(var(--muted-foreground))", fontSize:12 }} />
                      <YAxis tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      {[["PM Kisan","#10b981",0],["MGNREGA","#3b82f6",1],["Ayushman","#f59e0b",2],["PM Awas","#8b5cf6",3],["PM Ujjwala","#ec4899",4]].map(([n,c,i])=>(
                        <Area key={n as string} type="monotone" dataKey={n as string} stroke={c as string} fill={`url(#g${i})`} strokeWidth={2}/>
                      ))}
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="border-border bg-card/60">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <PieIcon className="h-4 w-4 text-blue-400" />
                    Beneficiaries by Sector (2024)
                  </CardTitle>
                  <CardDescription>Distribution across welfare sectors in Lakhs</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie data={sectorData} cx="50%" cy="50%" innerRadius={55} outerRadius={95}
                        dataKey="value" nameKey="name" paddingAngle={3}
                        label={({name,percent})=>`${name}: ${(percent*100).toFixed(0)}%`} labelLine={false}>
                        {sectorData.map((s,i)=><Cell key={i} fill={s.fill}/>)}
                      </Pie>
                      <Tooltip formatter={(v:number)=>[`${v}L`,""]} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">Top 5 States — Beneficiary Trend 2020–2024 (Lakhs)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={stateTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" tick={{ fill:"hsl(var(--muted-foreground))", fontSize:12 }} />
                    <YAxis tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    {[["Uttar Pradesh","#10b981"],["Maharashtra","#3b82f6"],["West Bengal","#f59e0b"],["Bihar","#8b5cf6"],["Madhya Pradesh","#ec4899"]].map(([n,c])=>(
                      <Line key={n as string} type="monotone" dataKey={n as string} stroke={c as string} strokeWidth={2.5} dot={{r:4}} activeDot={{r:6}}/>
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Region Summary */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(REGION_COLORS).map(([region, color]) => {
                const states = ALL_STATE_DATA.filter(s => s.region === region);
                const total = states.reduce((sum, s) => sum + s.beneficiaries[4], 0);
                const topState = [...states].sort((a,b) => b.beneficiaries[4] - a.beneficiaries[4])[0];
                return (
                  <Card key={region} className="border-border bg-card/60 hover:shadow-lg transition-all">
                    <CardContent className="pt-4 pb-4">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-3 h-3 rounded-full" style={{ background: color }} />
                        <span className="font-semibold text-sm">{region} India</span>
                        <span className="text-xs text-muted-foreground ml-auto">{states.length} states</span>
                      </div>
                      <div className="text-2xl font-bold text-green-400">{total.toFixed(1)}L</div>
                      <div className="text-xs text-muted-foreground mt-0.5">Total beneficiaries (2024)</div>
                      <div className="mt-2 text-xs">
                        <span className="text-muted-foreground">Top state: </span>
                        <span className="font-medium">{topState?.state}</span>
                      </div>
                      <div className="mt-2 text-xs">
                        <span className="text-muted-foreground">Top scheme: </span>
                        <span className="font-medium truncate">{topState?.topScheme}</span>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {/* ── STATES TAB ── */}
        {activeTab === "states" && (
          <div className="space-y-5">
            {/* Controls */}
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  value={searchQ} onChange={e => setSearchQ(e.target.value)}
                  placeholder="Search state..."
                  className="w-full pl-9 pr-4 py-2 text-sm bg-secondary border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500/40"
                />
              </div>
              <div className="flex gap-2 flex-wrap">
                {regions.map(r => (
                  <button key={r} onClick={() => setRegionFilter(r)}
                    className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                      regionFilter === r ? "text-white border-transparent" : "border-border text-muted-foreground hover:border-green-500/40"
                    }`}
                    style={{ background: regionFilter === r ? (r === "All" ? "#10b981" : REGION_COLORS[r]) : "" }}>
                    {r}
                  </button>
                ))}
              </div>
            </div>

            {/* Sort Row */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Filter className="h-3.5 w-3.5" />
              <span>Sort by:</span>
              {(["beneficiaries","score","yoy","coverage"] as const).map(k => (
                <button key={k} onClick={() => handleSort(k)}
                  className={`px-2.5 py-1 rounded-full border text-xs transition-all ${sortKey === k ? "bg-green-500 text-white border-green-500" : "border-border hover:border-green-500/40"}`}>
                  {k === "beneficiaries" ? "Beneficiaries" : k === "yoy" ? "YoY Growth" : k === "score" ? "Uptake Score" : "Coverage"}
                  <SortIcon k={k} />
                </button>
              ))}
              <span className="ml-auto text-muted-foreground">{filteredStates.length} states shown</span>
            </div>

            {/* Bar Chart */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">Beneficiaries by State (2024, Lakhs) — All States & UTs</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={Math.max(400, filteredStates.length * 22)}>
                  <BarChart data={filteredStates.map(s=>({ abbr: s.abbr, beneficiaries: s.beneficiaries[4], region: s.region }))} layout="vertical" margin={{ left: 14, right: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis type="number" tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} />
                    <YAxis type="category" dataKey="abbr" tick={{ fill:"hsl(var(--muted-foreground))", fontSize:10 }} width={28} />
                    <Tooltip formatter={(v:number) => [`${v.toFixed(1)}L`, "Beneficiaries"]} labelFormatter={l => filteredStates.find(s=>s.abbr===l)?.state ?? l} />
                    <Bar dataKey="beneficiaries" radius={[0,5,5,0]} label={{ position:"right", fontSize:10, fill:"hsl(var(--muted-foreground))", formatter:(v:number)=>`${v.toFixed(0)}L` }}>
                      {filteredStates.map((s,i) => (
                        <Cell key={i} fill={REGION_COLORS[s.region] ?? COLORS[i % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* State Cards Grid */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredStates.map((s, i) => (
                <Card key={s.state}
                  onClick={() => setSelectedState(selectedState?.state === s.state ? null : s)}
                  className={`border-border bg-card/60 cursor-pointer hover:shadow-lg transition-all ${selectedState?.state === s.state ? "ring-2 ring-green-500" : ""}`}>
                  <CardContent className="pt-4 pb-3">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="font-semibold text-sm">{s.state}</div>
                        <div className="flex items-center gap-1 mt-0.5">
                          <div className="w-2 h-2 rounded-full" style={{ background: REGION_COLORS[s.region] }} />
                          <span className="text-xs text-muted-foreground">{s.region}</span>
                        </div>
                      </div>
                      {i < 3 && <Star className="h-3.5 w-3.5 text-amber-400 fill-amber-400 flex-shrink-0" />}
                    </div>

                    {/* Top scheme badge */}
                    <div className="mb-2 px-2 py-1 rounded-md bg-green-500/10 border border-green-500/20">
                      <div className="text-xs text-green-400 font-medium truncate" title={s.topScheme}>
                        🏆 {s.topScheme}
                      </div>
                    </div>

                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Beneficiaries (2024)</span>
                        <span className="font-bold text-green-400">{s.beneficiaries[4].toFixed(1)}L</span>
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
                        <span className="text-muted-foreground">Budget (5-yr)</span>
                        <span className="font-medium">₹{(s.budget/100).toFixed(0)}K Cr</span>
                      </div>
                    </div>

                    {/* Score bar */}
                    <div className="mt-2">
                      <div className="h-1 bg-secondary rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-green-500 to-cyan-500 rounded-full"
                          style={{ width: `${s.score}%` }} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Selected State Detail */}
            {selectedState && (
              <Card className="border-green-500/40 bg-card/80 shadow-xl shadow-green-500/10">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-green-400" />
                    {selectedState.state} — Scheme Breakdown & 5-Year Trend
                  </CardTitle>
                  <CardDescription>Top schemes by % share of beneficiaries in {selectedState.state}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 gap-6">
                    {/* Pie of schemes */}
                    <div>
                      <h4 className="text-sm font-semibold mb-3">Scheme Distribution</h4>
                      <ResponsiveContainer width="100%" height={220}>
                        <PieChart>
                          <Pie data={selectedState.schemes} cx="50%" cy="50%" innerRadius={50} outerRadius={85}
                            dataKey="pct" nameKey="name" paddingAngle={2}>
                            {selectedState.schemes.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                          </Pie>
                          <Tooltip formatter={(v:number) => [`${v}%`, "Share"]} />
                          <Legend iconSize={10} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Bar: top scheme trend */}
                    <div>
                      <h4 className="text-sm font-semibold mb-3">Top Scheme Beneficiaries (Lakhs) — 2020–2024</h4>
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={YEARS.map((y,yi)=>({ year: String(y), beneficiaries: selectedState.topSchemeBeneficiaries[yi] }))}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis dataKey="year" tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} />
                          <YAxis tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} />
                          <Tooltip formatter={(v:number)=>[`${v}L`, selectedState.topScheme]} />
                          <Bar dataKey="beneficiaries" radius={[4,4,0,0]}>
                            {YEARS.map((_,i)=><Cell key={i} fill={COLORS[i % COLORS.length]}/>)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Scheme list */}
                  <div className="mt-4 space-y-2">
                    <h4 className="text-sm font-semibold">All Tracked Schemes in {selectedState.state}</h4>
                    {selectedState.schemes.map((sc, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                        <span className="text-xs flex-1">{sc.name}</span>
                        <div className="w-24 h-1.5 bg-secondary rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${sc.pct}%`, background: COLORS[i % COLORS.length] }} />
                        </div>
                        <span className="text-xs font-bold w-8 text-right" style={{ color: COLORS[i % COLORS.length] }}>{sc.pct}%</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* ── SCHEMES TAB ── */}
        {activeTab === "schemes" && (
          <div className="space-y-6">
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Award className="h-4 w-4 text-amber-400" />
                  Individual Scheme Deep Dive — 5-Year Trend
                </CardTitle>
                <CardDescription>Click any scheme to view its national beneficiary growth 2020–2024</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="flex gap-2 flex-wrap">
                  {Object.keys(schemeNationalData).map(s => (
                    <button key={s} onClick={() => setSelectedScheme(s)}
                      className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                        selectedScheme === s ? "bg-amber-500 text-white border-amber-500" : "border-border text-muted-foreground hover:border-amber-500/40"
                      }`}>{s}</button>
                  ))}
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={schemeBarData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" tick={{ fill:"hsl(var(--muted-foreground))", fontSize:12 }} />
                    <YAxis tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} />
                    <Tooltip formatter={(v:number)=>[`${v}L`, selectedScheme]} />
                    <Bar dataKey="Beneficiaries" radius={[6,6,0,0]}>
                      {schemeBarData.map((_,i)=><Cell key={i} fill={COLORS[i % COLORS.length]}/>)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Which states use this scheme most */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">States Where "{selectedScheme}" is the #1 Scheme</CardTitle>
                <CardDescription>States that have this as their most-adopted scheme</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {ALL_STATE_DATA.filter(s => s.topScheme === selectedScheme).map((s, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: REGION_COLORS[s.region] }} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold truncate">{s.state}</div>
                        <div className="text-xs text-muted-foreground">{s.region} • {s.beneficiaries[4].toFixed(1)}L beneficiaries</div>
                      </div>
                      <div className="text-xs font-bold text-amber-400">{s.score}/100</div>
                    </div>
                  ))}
                  {ALL_STATE_DATA.filter(s => s.topScheme === selectedScheme).length === 0 && (
                    <p className="text-sm text-muted-foreground col-span-3">No state has this as their #1 scheme — but it is tracked as a secondary scheme in multiple states.</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* All schemes table */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">National Scheme Comparison — Beneficiaries (Lakhs)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-2 pr-4 text-muted-foreground font-medium text-xs">Scheme</th>
                        {YEARS.map(y => <th key={y} className="text-right py-2 px-2 text-muted-foreground font-medium text-xs">{y}</th>)}
                        <th className="text-right py-2 pl-2 text-muted-foreground font-medium text-xs">Growth</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(schemeNationalData).map(([scheme, vals], idx) => {
                        const growth = (((vals[4]-vals[0])/vals[0])*100).toFixed(1);
                        return (
                          <tr key={scheme} className="border-b border-border/50 hover:bg-secondary/20 transition-colors">
                            <td className="py-2.5 pr-4 font-medium text-xs flex items-center gap-2">
                              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: COLORS[idx % COLORS.length] }}/>
                              {scheme}
                            </td>
                            {vals.map((v,i)=>(
                              <td key={i} className="text-right py-2.5 px-2 text-muted-foreground text-xs">{v}</td>
                            ))}
                            <td className="text-right py-2.5 pl-2 text-green-400 font-bold text-xs">+{growth}%</td>
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
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">Grouped Scheme Beneficiaries by Year (Lakhs)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={schemeAreaData} barGap={3}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="year" tick={{ fill:"hsl(var(--muted-foreground))", fontSize:12 }} />
                    <YAxis tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    {[["PM Kisan","#10b981"],["MGNREGA","#3b82f6"],["Ayushman","#f59e0b"],["PM Awas","#8b5cf6"]].map(([n,c])=>(
                      <Bar key={n as string} dataKey={n as string} fill={c as string} radius={[4,4,0,0]}/>
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* YoY Growth — ALL STATES */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">YoY Growth Rate — All 36 States & UTs (2023→2024)</CardTitle>
                <CardDescription>Ranked by year-on-year growth in scheme beneficiary adoption</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid sm:grid-cols-2 gap-x-8 gap-y-2">
                  {[...ALL_STATE_DATA].sort((a,b)=>b.yoy-a.yoy).map((s,i) => (
                    <div key={s.state} className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground w-4 text-right flex-shrink-0">{i+1}</span>
                      <span className="text-xs font-medium w-32 flex-shrink-0 truncate">{s.state}</span>
                      <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all"
                          style={{ width:`${(s.yoy/20)*100}%`, background: REGION_COLORS[s.region] }}/>
                      </div>
                      <span className="text-xs font-bold w-10 text-right flex-shrink-0" style={{ color: REGION_COLORS[s.region] }}>+{s.yoy}%</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Budget — ALL STATES */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">Budget Disbursed — Top 20 States (₹ Crore, 5-year total)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={480}>
                  <BarChart data={[...ALL_STATE_DATA].sort((a,b)=>b.budget-a.budget).slice(0,20).map(s=>({...s, budgetK: +(s.budget/100).toFixed(1)}))} layout="vertical" margin={{ left:14, right:50 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                    <XAxis type="number" tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} tickFormatter={v=>`₹${v}K Cr`}/>
                    <YAxis type="category" dataKey="abbr" tick={{ fill:"hsl(var(--muted-foreground))", fontSize:10 }} width={28}/>
                    <Tooltip formatter={(v:number)=>[`₹${v}K Crore`, "Disbursed"]} labelFormatter={(l:string) => ALL_STATE_DATA.find(s=>s.abbr===l)?.state ?? l}/>
                    <Bar dataKey="budgetK" radius={[0,5,5,0]} label={{ position:"right", fontSize:10, fill:"hsl(var(--muted-foreground))", formatter:(v:number)=>`₹${v}K Cr` }}>
                      {[...ALL_STATE_DATA].sort((a,b)=>b.budget-a.budget).slice(0,20).map((s,i)=>(
                        <Cell key={i} fill={REGION_COLORS[s.region] ?? COLORS[i%COLORS.length]}/>
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Coverage Scatter */}
            <Card className="border-border bg-card/60">
              <CardHeader>
                <CardTitle className="text-base">Uptake Score vs Coverage — All States (Bubble = YoY Growth)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  <ScatterChart margin={{ top:10, right:30, bottom:10, left:10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis type="number" dataKey="coverage" name="Coverage %" domain={[55,100]} tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} label={{ value:"Coverage %", position:"insideBottom", offset:-3, fill:"hsl(var(--muted-foreground))", fontSize:11 }}/>
                    <YAxis type="number" dataKey="score" name="Uptake Score" domain={[60,100]} tick={{ fill:"hsl(var(--muted-foreground))", fontSize:11 }} label={{ value:"Uptake Score", angle:-90, position:"insideLeft", fill:"hsl(var(--muted-foreground))", fontSize:11 }}/>
                    <ZAxis type="number" dataKey="yoy" range={[40,400]} />
                    <Tooltip cursor={{ strokeDasharray:"3 3" }} content={({ active, payload }) => {
                      if (active && payload?.length) {
                        const d = payload[0].payload;
                        return (
                          <div className="bg-card border border-border rounded-xl p-3 shadow-xl text-xs">
                            <p className="font-semibold">{d.state}</p>
                            <p>Coverage: {d.coverage}%</p>
                            <p>Score: {d.score}/100</p>
                            <p>YoY: +{d.yoy}%</p>
                            <p className="text-green-400">{d.topScheme}</p>
                          </div>
                        );
                      }
                      return null;
                    }}/>
                    {Object.entries(REGION_COLORS).map(([region, color]) => (
                      <Scatter key={region} name={region}
                        data={ALL_STATE_DATA.filter(s => s.region === region).map(s=>({ ...s, coverage: s.coverage, score: s.score, yoy: s.yoy }))}
                        fill={color} fillOpacity={0.7}/>
                    ))}
                    <Legend />
                  </ScatterChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Footer */}
        <div className="text-center py-4 text-xs text-muted-foreground border-t border-border">
          Data compiled from Ministry of Rural Development, DBT Mission, MoHFW, PIB & State Government Reports — 2020 to 2024 |
          Figures in Lakhs (L) · Gramin Saathi Analytics Engine · All 36 States & UTs of India
        </div>
      </div>
    </div>
  );
}
