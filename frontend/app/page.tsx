"use client";

import { useEffect, useState } from "react";
import { listPitchers, getPitcher, getDesign, PitcherRow, PitcherDetail, DesignSuggestion } from "@/lib/api";
import { ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

const gradeColor = (s: number) =>
  s >= 108 ? "#10b981" : s >= 103 ? "#84cc16" : s >= 98 ? "#eab308" : "#f87171";

export default function Dashboard() {
  const [pitchers, setPitchers] = useState<PitcherRow[]>([]);
  const [selected, setSelected] = useState<PitcherDetail | null>(null);
  const [design, setDesign] = useState<DesignSuggestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listPitchers(2024).then((p) => {
      setPitchers(p);
      if (p.length) pick(p[0].pitcher);
    }).finally(() => setLoading(false));
  }, []);

  function pick(id: number) {
    getPitcher(id, 2024).then(setSelected);
    getDesign(id).then((d) => setDesign(d.suggestions)).catch(() => setDesign([]));
  }

  if (loading) return <p className="text-slate-500">Loading leaderboard…</p>;

  return (
    <div className="grid grid-cols-[300px_1fr] gap-6">
      {/* Leaderboard */}
      <div>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
          2024 Stuff+ Leaderboard
        </h2>
        <div className="max-h-[75vh] space-y-1 overflow-y-auto pr-1">
          {pitchers.map((p, i) => (
            <button
              key={p.pitcher}
              onClick={() => pick(p.pitcher)}
              className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition ${
                selected?.pitcher === p.pitcher ? "bg-white/[0.06]" : "hover:bg-white/[0.03]"
              }`}
            >
              <span className="flex items-center gap-2">
                <span className="w-5 text-xs text-slate-500">{i + 1}</span>
                <span className="text-slate-200">{p.player_name}</span>
              </span>
              <span className="font-semibold" style={{ color: gradeColor(p.overall_stuff) }}>
                {p.overall_stuff}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Pitcher detail */}
      {selected && (
        <div className="space-y-6">
          <div className="flex items-end justify-between border-b border-white/5 pb-4">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">{selected.name}</h2>
              <p className="text-sm text-slate-500">{selected.total_pitches.toLocaleString()} pitches · 2024</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase tracking-wide text-slate-400">Overall Stuff+</p>
              <p className="text-3xl font-bold" style={{ color: gradeColor(selected.overall_stuff ?? 100) }}>
                {selected.overall_stuff}
              </p>
            </div>
          </div>

          {/* Arsenal */}
          <div>
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Arsenal</h3>
            <div className="space-y-2">
              {selected.arsenal.map((pitch) => (
                <div key={pitch.pitch_type} className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-baseline gap-3">
                      <span className="font-semibold text-slate-100">{pitch.pitch_name}</span>
                      <span className="text-xs text-slate-500">
                        {pitch.avg_velo.toFixed(1)} mph · {(pitch.pitches / selected.total_pitches * 100).toFixed(0)}% usage
                      </span>
                    </div>
                    <span className="rounded-lg px-3 py-1 text-sm font-bold" style={{ backgroundColor: gradeColor(pitch.stuff_plus) + "22", color: gradeColor(pitch.stuff_plus) }}>
                      {pitch.stuff_plus.toFixed(0)}
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-3 text-xs text-slate-400">
                    <div><span className="text-slate-500">Movement</span><br/>{pitch.avg_movement.toFixed(1)} in</div>
                    <div><span className="text-slate-500">Spin</span><br/>{pitch.avg_spin.toFixed(0)} rpm</div>
                    <div><span className="text-slate-500">Velo sep vs FB</span><br/>{pitch.velo_sep.toFixed(1)} mph</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Arsenal movement chart */}
          <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Arsenal: velocity vs. stuff grade
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
                  <XAxis type="number" dataKey="avg_velo" name="Velo" unit=" mph"
                    domain={["dataMin - 2", "dataMax + 2"]} tick={{ fill: "#64748b", fontSize: 11 }}
                    label={{ value: "Velocity (mph)", position: "bottom", fill: "#64748b", fontSize: 11 }} />
                  <YAxis type="number" dataKey="stuff_plus" name="Stuff+"
                    domain={[90, 120]} tick={{ fill: "#64748b", fontSize: 11 }}
                    label={{ value: "Stuff+", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }} />
                  <ZAxis type="number" dataKey="pitches" range={[60, 400]} />
                  <ReferenceLine y={100} stroke="#475569" strokeDasharray="3 3" />
                  <Tooltip
                    contentStyle={{ background: "#0d1220", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
                    formatter={(v: number, n: string) => [typeof v === "number" ? v.toFixed(1) : v, n]}
                    labelFormatter={() => ""}
                  />
                  <Scatter data={selected.arsenal} fill="#BD3039" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-1 text-center text-[11px] text-slate-600">
              Dashed line = league-average Stuff+ (100). Bubble size = pitch usage.
            </p>
          </div>

          {/* Pitch Lab - design recommendations */}
          {design.length > 0 && (
            <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Pitch Lab
              </h3>
              <p className="mb-3 text-[11px] text-slate-600">
                The single physical change the model projects would most improve each pitch.
              </p>
              <div className="space-y-2">
                {design.map((s) => (
                  <div key={s.pitch_type} className="flex items-center justify-between rounded-lg bg-white/[0.02] px-3 py-2 text-sm">
                    <span className="text-slate-300">
                      <span className="font-medium text-slate-100">{s.pitch_name}</span>
                      {": "}
                      {s.direction} {s.knob_label}
                      <span className="text-slate-500"> ({s.best_delta > 0 ? "+" : ""}{s.best_delta})</span>
                    </span>
                    <span className="font-semibold text-emerald-400">
                      +{s.projected_gain.toFixed(1)} Stuff+
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}