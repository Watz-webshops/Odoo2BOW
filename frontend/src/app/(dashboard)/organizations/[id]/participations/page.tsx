"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ScrollText } from "lucide-react";
import { api } from "@/lib/api";
import { centsToEur } from "@/lib/utils";

type Participation = {
  id: string;
  odoo_id: number;
  event_odoo_id: number;
  event_name: string | null;
  start_date: string | null;
  end_date: string | null;
  state: string | null;
  amount_paid_cents: number;
  parent_rrn: string | null;
  parent_name: string;
  parent_email: string | null;
  child_rrn: string | null;
  child_name: string;
};

export default function AdminParticipationsPage() {
  const params = useParams<{ id: string }>();
  const orgId = params.id;
  const searchParams = useSearchParams();
  const eventFilter = searchParams.get("event_odoo_id");

  const [year, setYear] = useState<number | "">("");

  const queryString = (() => {
    const p = new URLSearchParams();
    if (year) p.set("income_year", String(year));
    if (eventFilter) p.set("event_odoo_id", eventFilter);
    const s = p.toString();
    return s ? `?${s}` : "";
  })();

  const { data, isLoading } = useQuery({
    queryKey: ["org", orgId, "participations", year, eventFilter],
    queryFn: () => api.get<Participation[]>(`/organizations/${orgId}/participations${queryString}`),
  });

  return (
    <div className="space-y-5">
      <div className="text-sm">
        <Link href={`/organizations/${orgId}`} className="text-brand-600 hover:underline inline-flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Terug naar organisatie
        </Link>
      </div>

      <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
        <ScrollText className="w-5 h-5 text-brand-600" />
        Deelnames (admin)
      </h1>

      <div className="flex items-center gap-3 text-sm">
        <label className="text-gray-600">Inkomstenjaar:</label>
        <select
          value={year}
          onChange={(e) => setYear(e.target.value ? parseInt(e.target.value, 10) : "")}
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">Alle</option>
          {[2024, 2025, 2026, 2027].map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
        {eventFilter && (
          <span className="text-xs text-gray-500">Gefilterd op event {eventFilter} ·{" "}
            <Link href={`/organizations/${orgId}/participations`} className="text-brand-600 hover:underline">
              wis filter
            </Link>
          </span>
        )}
      </div>

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {data && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Event</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Periode</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
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
                    {p.start_date && p.end_date ? `${p.start_date} → ${p.end_date}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      p.state === "open" ? "bg-green-100 text-green-700" :
                      p.state === "done" ? "bg-blue-100 text-blue-700" :
                      p.state === "cancel" ? "bg-red-100 text-red-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>{p.state ?? "—"}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-700">{centsToEur(p.amount_paid_cents)}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {p.parent_name || "—"}
                    <div className="text-xs font-mono text-gray-400">{p.parent_rrn || "—"}</div>
                    {p.parent_email && <div className="text-xs text-gray-500">{p.parent_email}</div>}
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {p.child_name || "—"}
                    <div className="text-xs font-mono text-gray-400">{p.child_rrn || "—"}</div>
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
