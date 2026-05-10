"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Search, Users } from "lucide-react";
import { api } from "@/lib/api";

type Beneficiary = {
  parent_rrn: string;
  parent_name: string;
  parent_email: string | null;
  child_rrn: string;
  child_name: string;
};

export default function AdminBeneficiariesPage() {
  const params = useParams<{ id: string }>();
  const orgId = params.id;
  const [q, setQ] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["org", orgId, "beneficiaries"],
    queryFn: () => api.get<Beneficiary[]>(`/organizations/${orgId}/beneficiaries`),
  });

  const filtered = data?.filter((b) => {
    if (!q) return true;
    const needle = q.toLowerCase();
    return (
      b.parent_name.toLowerCase().includes(needle) ||
      b.child_name.toLowerCase().includes(needle) ||
      b.parent_rrn.includes(q) ||
      b.child_rrn.includes(q) ||
      (b.parent_email || "").toLowerCase().includes(needle)
    );
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
        <Users className="w-5 h-5 text-brand-600" />
        Begunstigden (admin)
      </h1>

      <div className="relative max-w-sm">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Zoek op naam, RRN of e-mail..."
          className="w-full border border-gray-300 rounded-lg pl-9 pr-3 py-2 text-sm"
        />
      </div>

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {filtered && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ouder</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">RRN ouder</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">E-mail</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Kind</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">RRN kind</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((b, i) => (
                <tr key={`${b.parent_rrn}-${b.child_rrn}-${i}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">{b.parent_name || "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{b.parent_rrn}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{b.parent_email || "—"}</td>
                  <td className="px-4 py-3 text-gray-900">{b.child_name || "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{b.child_rrn}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Geen begunstigden</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
