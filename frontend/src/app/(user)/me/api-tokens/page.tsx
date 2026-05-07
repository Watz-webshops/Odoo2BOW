"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Trash2, Copy, Check } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { ApiToken, ApiTokenCreated } from "@/types/organization";

export default function MyApiTokensPage() {
  const qc = useQueryClient();
  const [newToken, setNewToken] = useState<ApiTokenCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: tokens } = useQuery({
    queryKey: ["me", "api-tokens"],
    queryFn: () => api.get<ApiToken[]>("/me/api-tokens"),
  });

  const create = useMutation({
    mutationFn: (label: string) => api.post<ApiTokenCreated>("/me/api-tokens", { label: label || null }),
    onSuccess: (t) => {
      setNewToken(t);
      qc.invalidateQueries({ queryKey: ["me", "api-tokens"] });
    },
  });

  const revoke = useMutation({
    mutationFn: (id: string) => api.delete(`/me/api-tokens/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me", "api-tokens"] }),
  });

  function copy(s: string) {
    navigator.clipboard.writeText(s);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-5 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">API Tokens</h1>
          <p className="text-sm text-gray-500 mt-1">Gebruik deze om vanuit Odoo exports aan te maken via de API.</p>
        </div>
        <button
          onClick={() => {
            const label = prompt("Label voor token (optioneel):") ?? "";
            create.mutate(label);
          }}
          className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-3 py-2 rounded-lg"
        >
          <KeyRound className="w-4 h-4" />
          Nieuw token
        </button>
      </div>

      {newToken && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm">
          <p className="font-medium text-amber-800 mb-2">Token aangemaakt — sla op, wordt niet opnieuw getoond.</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-white border border-amber-200 rounded px-3 py-2 text-xs break-all font-mono">
              {newToken.raw_token}
            </code>
            <button onClick={() => copy(newToken.raw_token)} className="p-2 rounded-lg hover:bg-amber-100 text-amber-700">
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <button onClick={() => setNewToken(null)} className="mt-2 text-xs text-amber-600 hover:underline">Sluiten</button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {tokens && tokens.length === 0 && (
          <p className="px-4 py-3 text-sm text-gray-500">Nog geen tokens</p>
        )}
        {tokens && tokens.map((t) => (
          <div key={t.id} className="flex items-center justify-between px-4 py-3 border-b border-gray-100 last:border-0">
            <div>
              <p className="text-sm font-medium text-gray-900">{t.label ?? "Naamloos"}</p>
              <p className="text-xs text-gray-500">Aangemaakt {formatDate(t.created_at)}</p>
            </div>
            {t.revoked_at ? (
              <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded-full">Ingetrokken</span>
            ) : (
              <button
                onClick={() => { if (confirm("Token intrekken?")) revoke.mutate(t.id); }}
                className="p-1.5 rounded-lg text-red-500 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
