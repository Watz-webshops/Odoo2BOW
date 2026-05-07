"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { centsToEur } from "@/lib/utils";

type Participation = {
  id: string;
  export_id: string;
  income_year: number;
  event_name: string | null;
  start_date: string;
  end_date: string;
  days: number;
  amount_paid_cents: number;
  parent_rrn: string;
  parent_name: string;
  child_rrn: string;
  child_name: string;
};

export default function ParticipationsPage() {
  const [year, setYear] = useState<number | "">("");
  const { data, isLoading } = useQuery({
    queryKey: ["me", "participations", year],
    queryFn: () =>
      api.get<Participation[]>(
        `/me/participations${year ? `?income_year=${year}` : ""}`
      ),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-gray-900">Deelnames</h1>

      <div className="flex items-center gap-3">
        <label className="text-sm text-gray-600">Inkomstenjaar:</label>
        <select
          value={year}
          onChange={(e) => setYear(e.target.value ? parseInt(e.target.value, 10) : "")}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">Alle</option>
          {[2024, 2025, 2026].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {data && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Event</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Periode</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Dagen</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Bedrag</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ouder</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Kind</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">{p.event_name ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">
                    {p.start_date} → {p.end_date}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{p.days}</td>
                  <td className="px-4 py-3 text-gray-700">{centsToEur(p.amount_paid_cents)}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {p.parent_name || "—"}
                    <div className="text-xs font-mono text-gray-400">{p.parent_rrn}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {p.child_name || "—"}
                    <div className="text-xs font-mono text-gray-400">{p.child_rrn}</div>
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">Geen deelnames</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
