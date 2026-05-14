"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { ExportRecord, ExportStatus } from "@/types/export";
import { centsToEur } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { Download, AlertTriangle } from "lucide-react";

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

export default function ExportDetailPageClient() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const { data: exp } = useQuery({
    queryKey: ["exports", id],
    queryFn: () => api.get<ExportRecord>(`/exports/belcotax/${id}`),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "pending" || s === "processing" ? 2000 : false;
    },
  });

  async function downloadXml() {
    const token = (await import("@/lib/auth")).getAccessToken();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const res = await fetch(`${apiUrl}/api/v1/exports/belcotax/${id}/xml`, {
      headers: { Authorization: `Bearer ${token ?? ""}` },
    });
    if (!res.ok) return alert("Download mislukt");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `belcotax_${id}.xml`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!exp) return <p className="text-sm text-gray-500">Laden...</p>;

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Export detail</h1>
          <p className="text-xs font-mono text-gray-500 mt-0.5">{exp.export_id}</p>
        </div>
        <span className={cn("px-3 py-1 rounded-full text-sm font-medium", STATUS_STYLES[exp.status])}>
          {STATUS_LABELS[exp.status]}
        </span>
      </div>

      {(exp.status === "pending" || exp.status === "processing") && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-700">
          Export wordt verwerkt — pagina ververst automatisch...
        </div>
      )}

      {exp.status === "failed" && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          <p className="font-medium mb-1">Export mislukt</p>
          <pre className="whitespace-pre-wrap font-mono text-xs">{exp.error_detail}</pre>
        </div>
      )}

      {exp.summary && (
        <>
          <div className="bg-white rounded-xl border border-gray-200 p-5 grid grid-cols-2 gap-4 text-sm">
            <Stat label="Aantal fiches" value={exp.summary.fiche_count} />
            <Stat label="Totaalbedrag" value={centsToEur(exp.summary.total_amount_cents)} />
            <Stat label="Totaal dagen" value={exp.summary.total_days} />
            <Stat label="Overgeslagen" value={exp.summary.skipped_count} />
          </div>

          {exp.summary.warnings.length > 0 && (
            <section className="space-y-2">
              <h2 className="font-medium text-gray-900 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Waarschuwingen ({exp.summary.warnings.length})
              </h2>
              <div className="bg-amber-50 border border-amber-200 rounded-xl divide-y divide-amber-100">
                {exp.summary.warnings.map((w, i) => (
                  <div key={i} className="px-4 py-3 text-sm">
                    <p className="text-amber-800">{w.message}</p>
                    <p className="text-xs text-amber-600 mt-0.5">
                      Ouder: {w.parent_rrn} · Kind: {w.child_rrn}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {exp.status === "completed" && (
        <button
          onClick={downloadXml}
          className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
        >
          <Download className="w-4 h-4" />
          XML downloaden
        </button>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-gray-500 text-xs">{label}</p>
      <p className="font-semibold text-gray-900 mt-0.5">{value}</p>
    </div>
  );
}
