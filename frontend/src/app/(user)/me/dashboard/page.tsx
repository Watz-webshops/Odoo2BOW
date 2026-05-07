"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { centsToEur } from "@/lib/utils";
import type { Organization } from "@/types/organization";
import type { ExportRecord } from "@/types/export";

export default function UserDashboard() {
  const { data: org } = useQuery({
    queryKey: ["me", "organization"],
    queryFn: () => api.get<Organization>("/me/organization"),
  });

  const { data: exports } = useQuery({
    queryKey: ["me", "exports"],
    queryFn: () => api.get<ExportRecord[]>("/me/exports"),
  });

  const completed = exports?.filter((e) => e.status === "completed") ?? [];
  const totalFiches = completed.reduce((s, e) => s + (e.summary?.fiche_count ?? 0), 0);
  const totalAmount = completed.reduce((s, e) => s + (e.summary?.total_amount_cents ?? 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
        {org && <p className="text-sm text-gray-500 mt-1">{org.name} · KBO {org.kbo}</p>}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Stat label="Exports (voltooid)" value={completed.length} />
        <Stat label="Totaal fiches" value={totalFiches} />
        <Stat label="Totaal bedrag" value={centsToEur(totalAmount)} />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
    </div>
  );
}
