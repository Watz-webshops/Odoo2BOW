"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ExportRecord } from "@/types/export";
import type { Organization } from "@/types/organization";
import { centsToEur } from "@/lib/utils";

export default function DashboardPage() {
  const { data: exports } = useQuery({
    queryKey: ["exports"],
    queryFn: () => api.get<ExportRecord[]>("/exports"),
  });

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.get<Organization[]>("/organizations"),
  });

  const completed = exports?.filter((e) => e.status === "completed") ?? [];
  const totalFiches = completed.reduce((s, e) => s + (e.summary?.fiche_count ?? 0), 0);
  const totalAmount = completed.reduce((s, e) => s + (e.summary?.total_amount_cents ?? 0), 0);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-3 gap-4">
        <Stat label="Organisaties" value={orgs?.length ?? 0} />
        <Stat label="Exports (voltooid)" value={completed.length} />
        <Stat label="Totaal fiches" value={totalFiches} />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-medium text-gray-700 mb-3">Totaal gedeclareerd bedrag</h2>
        <p className="text-3xl font-bold text-gray-900">{centsToEur(totalAmount)}</p>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
    </div>
  );
}
