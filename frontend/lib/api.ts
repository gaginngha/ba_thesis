const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}/api/v1${path}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value) url.searchParams.set(key, value);
    });
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface Municipality {
  bfs_number: number;
  name: string;
  canton_abbreviation: string;
  population: number | null;
  municipality_type: string | null;
  is_active: boolean;
}

export interface Canton {
  bfs_number: number;
  abbreviation: string;
  name_de: string;
}

export interface FinancialData {
  municipality_bfs: number;
  year: number;
  total_revenue: number | null;
  tax_revenue: number | null;
  total_expenditure: number | null;
  operating_result: number | null;
  net_debt: number | null;
  revenue_per_capita: number | null;
  expenditure_per_capita: number | null;
  net_debt_per_capita: number | null;
  self_financing_ratio: number | null;
  debt_ratio: number | null;
}

export interface CompositeScore {
  municipality_bfs: number;
  municipality_name: string | null;
  canton_abbreviation: string | null;
  year: number;
  financial_health_score: number | null;
  tax_attractiveness_score: number | null;
  demographic_vitality_score: number | null;
  economic_strength_score: number | null;
  composite_score: number | null;
  peer_group: string | null;
  national_rank: number | null;
}

export interface TimeSeriesPoint {
  year: number;
  value: number | null;
}

export interface TrendResult {
  direction: string;
  slope: number;
  r_squared: number;
  confidence: number;
}

export interface ForecastPoint {
  year: number;
  predicted_value: number;
  confidence: number;
}

export interface ForecastResponse {
  metric: string;
  municipality_bfs: number;
  historical: { year: number; value: number | null }[];
  trend: TrendResult;
  forecast: ForecastPoint[];
  anomalies: { year: number; value: number }[];
}

export interface PeerGroupBenchmark {
  municipality: { bfs_number: number; name: string; canton: string; population: number | null };
  peer_group: string;
  peer_group_size: number;
  scores: Record<string, number | null>;
  peer_group_avg: Record<string, number | null>;
  peer_group_median: Record<string, number | null>;
  percentile_rank: Record<string, number | null>;
  top_5_peers: { municipality_bfs: number; name: string; canton: string; composite_score: number }[];
}

export const api = {
  municipalities: {
    list: (params?: Record<string, string>) =>
      fetchAPI<Municipality[]>("/municipalities", params),
    get: (bfs: number) =>
      fetchAPI<Municipality>(`/municipalities/${bfs}`),
    cantons: () =>
      fetchAPI<Canton[]>("/municipalities/cantons"),
  },
  financial: {
    get: (bfs: number, params?: Record<string, string>) =>
      fetchAPI<FinancialData[]>(`/financial/${bfs}`, params),
    timeseries: (bfs: number, metric: string) =>
      fetchAPI<TimeSeriesPoint[]>(`/financial/${bfs}/timeseries/${metric}`),
  },
  demographics: {
    timeseries: (bfs: number, metric: string) =>
      fetchAPI<TimeSeriesPoint[]>(`/demographics/${bfs}/timeseries/${metric}`),
  },
  scores: {
    rankings: (params?: Record<string, string>) =>
      fetchAPI<CompositeScore[]>("/scores/rankings", params),
    get: (bfs: number) =>
      fetchAPI<CompositeScore[]>(`/scores/${bfs}`),
  },
  trends: {
    forecast: (bfs: number, metric: string, years?: number) =>
      fetchAPI<ForecastResponse>(`/trends/${bfs}/forecast/${metric}`, years ? { forecast_years: years.toString() } : undefined),
  },
  benchmark: {
    peerGroup: (bfs: number, year?: number) =>
      fetchAPI<PeerGroupBenchmark>(`/benchmark/${bfs}/peer-group`, year ? { year: year.toString() } : undefined),
  },
  reports: {
    downloadPdf: (bfs: number) =>
      `${API_BASE}/api/v1/reports/${bfs}/pdf`,
  },
};
