"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { centsToEur } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ExportRecord, ExportStatus } from "@/types/export";

const STATUS_STYLES: Record<ExportStatus, string> = {
  pending: "bg-gray-100 text-gray-600",
  processing: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<ExportStatus, string> = {
  pending: "In wacht",
  processing: "Verwerking",
  completed: "Voltooid",
  failed: "Mislukt",
};

export default function MyExportsPage() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [year, setYear] = useState(new Date().getFullYear());

  const { data: exports, isLoading } = useQuery({
    queryKey: ["me", "exports"],
    queryFn: () => api.get<ExportRecord[]>("/me/exports"),
    refetchInterval: (q) => {
      const hasActive = q.state.data?.some((e) => e.status === "pending" || e.status === "processing");
      return hasActive ? 2000 : false;
    },
  });

  const generateFromLocal = useMutation({
    mutationFn: (income_year: number) =>
      api.post<{ export_id: string }>("/me/exports/from-local", { income_year }),
    onSuccess: () => {
      setShowModal(false);
      qc.invalidateQueries({ queryKey: ["me", "exports"] });
    },
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Mijn exports</h1>
        <div className="flex items-center gap-2">
          <Link
            href="/me/exports/preview"
            className="inline-flex items-center gap-1.5 bg-white hover:bg-gray-50 border border-gray-200 text-gray-900 text-sm font-medium px-3 py-2 rounded-lg"
          >
            <Eye className="w-4 h-4 text-brand-600" />
            Voorvertonen
          </Link>
          <button onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-3 py-2 rounded-lg">
            <Zap className="w-4 h-4" />
            Genereer XML uit Odoo data
          </button>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-800">
        Exports kan je ook aanmaken via de API met een Bearer token (zie <Link href="/me/api-tokens" className="underline">API Tokens</Link>).
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm space-y-4">
            <h2 className="font-semibold text-gray-900">Genereer XML uit Odoo data</h2>
            <p className="text-sm text-gray-600">
              De middleware gebruikt de gesyncde Odoo data om de Belcotax 281.86 XML te genereren.
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Inkomstenjaar</label>
              <select value={year} onChange={(e) => setYear(parseInt(e.target.value, 10))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                {[2024, 2025, 2026, 2027].map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
            {generateFromLocal.error ? (
              <p className="text-sm text-red-600">Fout — controleer of je Odoo connectie gesynced is</p>
            ) : null}
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50">
                Annuleren
              </button>
              <button onClick={() => generateFromLocal.mutate(year)} disabled={generateFromLocal.isPending}
                className="px-4 py-2 text-sm rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium disabled:opacity-50">
                {generateFromLocal.isPending ? "Bezig..." : "Genereren"}
              </button>
            </div>
          </div>
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {exports && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Export ID</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fiches</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Bedrag</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {exports.map((e) => (
                <tr key={e.export_id} className="hover:bg-gray-50">
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
                    <Link href={`/me/exports/${e.export_id}`} className="text-brand-600 hover:underline font-medium">
                      Details
                    </Link>
                  </td>
                </tr>
              ))}
              {exports.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Nog geen exports</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
