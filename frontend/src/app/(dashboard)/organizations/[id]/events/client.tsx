"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Calendar } from "lucide-react";
import { api } from "@/lib/api";
import { useRouteSegment } from "@/lib/route";

type OdooEvent = {
  id: string;
  odoo_id: number;
  name: string | null;
  date_begin: string | null;
  date_end: string | null;
  registration_count: number;
  synced_at: string | null;
};

export function AdminEventsPageClient() {
  const orgId = useRouteSegment("/organizations");

  const { data, isLoading } = useQuery({
    queryKey: ["org", orgId, "events"],
    queryFn: () => api.get<OdooEvent[]>(`/organizations/${orgId}/events`),
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
        <Calendar className="w-5 h-5 text-brand-600" />
        Events / Kampen (admin)
      </h1>

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {data && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Naam</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Periode</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Inschrijvingen</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Odoo ID</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{e.name ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">
                    {e.date_begin && e.date_end ? `${e.date_begin} → ${e.date_end}` : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{e.registration_count}</td>
                  <td className="px-4 py-3 text-xs font-mono text-gray-500">{e.odoo_id}</td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/organizations/${orgId}/participations?event_odoo_id=${e.odoo_id}`}
                      className="text-brand-600 hover:underline font-medium text-xs"
                    >
                      Bekijk inschrijvingen
                    </Link>
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                  Nog geen events gesyncd. Klik op <strong>Initial bootstrap</strong> in Odoo Connectie.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
