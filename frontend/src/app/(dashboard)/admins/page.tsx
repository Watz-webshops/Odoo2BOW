"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, KeyRound, Copy, Check } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

type Admin = {
  id: string;
  email: string;
  created_at: string;
  last_login: string | null;
};

type AdminCreated = Admin & { raw_password: string };

export default function AdminsPage() {
  const qc = useQueryClient();
  const [newPassword, setNewPassword] = useState<{ email: string; password: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: admins, isLoading } = useQuery({
    queryKey: ["admins"],
    queryFn: () => api.get<Admin[]>("/admins"),
  });

  const create = useMutation({
    mutationFn: (email: string) => api.post<AdminCreated>("/admins", { email }),
    onSuccess: (a) => {
      setNewPassword({ email: a.email, password: a.raw_password });
      qc.invalidateQueries({ queryKey: ["admins"] });
    },
  });

  const del = useMutation({
    mutationFn: (id: string) => api.delete(`/admins/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admins"] }),
  });

  const reset = useMutation({
    mutationFn: (id: string) => api.post<{ raw_password: string }>(`/admins/${id}/reset-password`, {}),
    onSuccess: (r, id) => {
      const a = admins?.find((x) => x.id === id);
      if (a) setNewPassword({ email: a.email, password: r.raw_password });
    },
  });

  function copy(s: string) {
    navigator.clipboard.writeText(s);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Admins</h1>
        <button
          onClick={() => {
            const email = prompt("Email van nieuwe admin:");
            if (email) create.mutate(email);
          }}
          className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-3 py-2 rounded-lg"
        >
          <Plus className="w-4 h-4" />
          Nieuwe admin
        </button>
      </div>

      {newPassword && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm">
          <p className="font-medium text-amber-800 mb-2">
            Wachtwoord voor {newPassword.email} — sla op, wordt niet opnieuw getoond.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-white border border-amber-200 rounded px-3 py-2 text-xs break-all font-mono">
              {newPassword.password}
            </code>
            <button onClick={() => copy(newPassword.password)} className="p-2 rounded-lg hover:bg-amber-100 text-amber-700">
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <button onClick={() => setNewPassword(null)} className="mt-2 text-xs text-amber-600 hover:underline">
            Sluiten
          </button>
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {admins && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">E-mail</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Aangemaakt</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Laatste login</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {admins.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.email}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(a.created_at)}</td>
                  <td className="px-4 py-3 text-gray-500">{a.last_login ? formatDate(a.last_login) : "—"}</td>
                  <td className="px-4 py-3 text-right space-x-1">
                    <button
                      onClick={() => { if (confirm("Reset wachtwoord?")) reset.mutate(a.id); }}
                      className="p-1.5 rounded-lg text-amber-600 hover:bg-amber-50"
                      title="Reset password"
                    >
                      <KeyRound className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => { if (confirm(`Admin ${a.email} verwijderen?`)) del.mutate(a.id); }}
                      className="p-1.5 rounded-lg text-red-500 hover:bg-red-50"
                      title="Verwijderen"
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
