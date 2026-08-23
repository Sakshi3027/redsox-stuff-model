import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stuff Model — Pitch Quality Grades",
  description: "Grading MLB pitch quality from physics, on real Statcast data",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-white/5 bg-[#0d1220] px-8 py-5">
          <div className="mx-auto flex max-w-6xl items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#BD3039]/20 text-[#BD3039] font-bold">S+</span>
            <div>
              <h1 className="text-sm font-semibold tracking-tight">Stuff Model</h1>
              <p className="text-[11px] text-slate-500">Pitch quality from physics · real Statcast data</p>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-8 py-8">{children}</main>
      </body>
    </html>
  );
}