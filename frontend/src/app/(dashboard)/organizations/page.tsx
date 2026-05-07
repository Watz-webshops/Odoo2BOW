"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Organization } from "@/types/organization";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import { Plus } from "lucide-react";

export default function OrganizationsPage() {
  const { data: orgs, isLoading } = useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.get<Organization[]>("/organizations"),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Organisaties</h1>
        <Link
          href="/organizations/new"
          className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-3 py-2 rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nieuwe organisatie
        </Link>
      </div>

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {orgs && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Naam</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">KBO</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Stad</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Aangemaakt</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {orgs.map((org) => (
                <tr key={org.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900">{org.name}</td>
                  <td className="px-4 py-3 text-gray-600">{org.kbo}</td>
                  <td className="px-4 py-3 text-gray-600">{org.city ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(org.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/organizations/${org.id}`}
                      className="text-brand-600 hover:underline font-medium"
                    >
                      Beheer
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
