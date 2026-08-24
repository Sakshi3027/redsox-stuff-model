const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

export interface PitcherRow {
  pitcher: number;
  player_name: string;
  game_year: number;
  total_pitches: number;
  num_pitch_types: number;
  overall_stuff: number;
}

export interface ArsenalPitch {
  pitch_type: string;
  pitch_name: string;
  stuff_plus: number;
  pitches: number;
  avg_velo: number;
  avg_movement: number;
  avg_spin: number;
  velo_sep: number;
}

export interface PitcherDetail {
  pitcher: number;
  name: string;
  year: number;
  overall_stuff: number | null;
  total_pitches: number;
  arsenal: ArsenalPitch[];
}

export interface DesignSuggestion {
  pitch_type: string;
  pitch_name: string;
  knob_label: string;
  direction: string;
  best_delta: number;
  projected_gain: number;
  base_stuff: number;
}

export async function listPitchers(year = 2024): Promise<PitcherRow[]> {
  const res = await fetch(`${API_BASE}/pitchers?year=${year}&limit=100`);
  if (!res.ok) throw new Error(`pitchers failed: ${res.status}`);
  return res.json();
}

export async function getPitcher(id: number, year = 2024): Promise<PitcherDetail> {
  const res = await fetch(`${API_BASE}/pitcher/${id}?year=${year}`);
  if (!res.ok) throw new Error(`pitcher failed: ${res.status}`);
  return res.json();
}

export async function getDesign(id: number): Promise<{ suggestions: DesignSuggestion[] }> {
  const res = await fetch(`${API_BASE}/design/${id}`);
  if (!res.ok) throw new Error(`design failed: ${res.status}`);
  return res.json();
}