"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { Search } from "lucide-react";

type Beneficiary = {
  parent_rrn: string;
  parent_name: string;
  child_rrn: string;
  child_name: string;
  child_birth_date: string | null;
};

export default function BeneficiariesPage() {
  const [q, setQ] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["me", "beneficiaries"],
    queryFn: () => api.get<Beneficiary[]>("/me/beneficiaries"),
  });

  const filtered = data?.filter((b) => {
    if (!q) return true;
    const needle = q.toLowerCase();
    return (
      b.parent_name.toLowerCase().includes(needle) ||
      b.child_name.toLowerCase().includes(needle) ||
      b.parent_rrn.includes(q) ||
      b.child_rrn.includes(q)
    );
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-gray-900">Begunstigden</h1>

      <div className="relative max-w-sm">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Zoek op naam of RRN..."
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
                <th className="text-left px-4 py-3 font-medium text-gray-600">Kind</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">RRN kind</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Geboorte</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((b, i) => (
                <tr key={`${b.parent_rrn}-${b.child_rrn}-${i}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">{b.parent_name || "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{b.parent_rrn}</td>
                  <td className="px-4 py-3 text-gray-900">{b.child_name || "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{b.child_rrn}</td>
                  <td className="px-4 py-3 text-gray-600">{b.child_birth_date ?? "—"}</td>
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
