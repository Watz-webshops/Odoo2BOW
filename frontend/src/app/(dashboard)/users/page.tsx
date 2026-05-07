"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, KeyRound, Copy, Check } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { Organization } from "@/types/organization";

type User = {
  id: string;
  org_id: string;
  email: string;
  created_at: string;
  last_login: string | null;
};

type UserCreated = User & { raw_password: string };

export default function UsersPage() {
  const qc = useQueryClient();
  const [creds, setCreds] = useState<{ email: string; password: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users"),
  });

  const { data: orgs } = useQuery({
    queryKey: ["organizations"],
    queryFn: () => api.get<Organization[]>("/organizations"),
  });

  const create = useMutation({
    mutationFn: (body: { email: string; org_id: string }) => api.post<UserCreated>("/users", body),
    onSuccess: (u) => {
      setCreds({ email: u.email, password: u.raw_password });
      qc.invalidateQueries({ queryKey: ["users"] });
    },
  });

  const del = useMutation({
    mutationFn: (id: string) => api.delete(`/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  const reset = useMutation({
    mutationFn: (id: string) => api.post<{ raw_password: string }>(`/users/${id}/reset-password`, {}),
    onSuccess: (r, id) => {
      const u = users?.find((x) => x.id === id);
      if (u) setCreds({ email: u.email, password: r.raw_password });
    },
  });

  function copy(s: string) {
    navigator.clipboard.writeText(s);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function startCreate() {
    const email = prompt("Email van nieuwe user:");
    if (!email) return;
    if (!orgs || orgs.length === 0) {
      alert("Maak eerst een organisatie aan.");
      return;
    }
    const orgChoice = orgs.map((o, i) => `${i + 1}. ${o.name} (${o.kbo})`).join("\n");
    const idx = prompt(`Kies een organisatie:\n${orgChoice}\n\nGeef het nummer in:`);
    if (!idx) return;
    const i = parseInt(idx, 10) - 1;
    if (Number.isNaN(i) || !orgs[i]) return alert("Ongeldige keuze");
    create.mutate({ email, org_id: orgs[i].id });
  }

  const orgName = (id: string) => orgs?.find((o) => o.id === id)?.name ?? "—";

  return (
    <div className="space-y-5 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Users</h1>
        <button
          onClick={startCreate}
          className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-3 py-2 rounded-lg"
        >
          <Plus className="w-4 h-4" />
          Nieuwe user
        </button>
      </div>

      {creds && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm">
          <p className="font-medium text-amber-800 mb-2">
            Wachtwoord voor {creds.email} — sla op, wordt niet opnieuw getoond.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-white border border-amber-200 rounded px-3 py-2 text-xs break-all font-mono">
              {creds.password}
            </code>
            <button onClick={() => copy(creds.password)} className="p-2 rounded-lg hover:bg-amber-100 text-amber-700">
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <button onClick={() => setCreds(null)} className="mt-2 text-xs text-amber-600 hover:underline">
            Sluiten
          </button>
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {users && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">E-mail</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Organisatie</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Aangemaakt</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Laatste login</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{u.email}</td>
                  <td className="px-4 py-3 text-gray-600">{orgName(u.org_id)}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(u.created_at)}</td>
                  <td className="px-4 py-3 text-gray-500">{u.last_login ? formatDate(u.last_login) : "—"}</td>
                  <td className="px-4 py-3 text-right space-x-1">
                    <button
                      onClick={() => { if (confirm("Reset wachtwoord?")) reset.mutate(u.id); }}
                      className="p-1.5 rounded-lg text-amber-600 hover:bg-amber-50"
                    >
                      <KeyRound className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => { if (confirm(`User ${u.email} verwijderen?`)) del.mutate(u.id); }}
                      className="p-1.5 rounded-lg text-red-500 hover:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
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
