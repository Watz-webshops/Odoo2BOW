"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ExportRecord, ExportStatus } from "@/types/export";
import { centsToEur, formatDate } from "@/lib/utils";
import Link from "next/link";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<ExportStatus, string> = {
  pending:    "bg-gray-100 text-gray-600",
  processing: "bg-blue-100 text-blue-700",
  completed:  "bg-green-100 text-green-700",
  failed:     "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<ExportStatus, string> = {
  pending:    "In wacht",
  processing: "Verwerking",
  completed:  "Voltooid",
  failed:     "Mislukt",
};

export default function ExportsPage() {
  const { data: exports, isLoading } = useQuery({
    queryKey: ["exports"],
    queryFn: () => api.get<ExportRecord[]>("/exports"),
    refetchInterval: (query) => {
      const hasActive = query.state.data?.some(
        (e) => e.status === "pending" || e.status === "processing"
      );
      return hasActive ? 2000 : false;
    },
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-gray-900">Exports</h1>

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {exports && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Export ID</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fiches</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Totaalbedrag</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {exports.map((e) => (
                <tr key={e.export_id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">{e.export_id}</td>
                  <td className="px-4 py-3">
                    <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", STATUS_STYLES[e.status])}>
                      {STATUS_LABELS[e.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{e.summary?.fiche_count ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {e.summary ? centsToEur(e.summary.total_amount_cents) : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/exports/${e.export_id}`} className="text-brand-600 hover:underline font-medium">
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
              {exports.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-400">Geen exports gevonden</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
