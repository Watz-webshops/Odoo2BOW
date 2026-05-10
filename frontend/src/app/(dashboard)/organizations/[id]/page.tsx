"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Organization, ApiToken, ApiTokenCreated } from "@/types/organization";
import { formatDate } from "@/lib/utils";
import { useState } from "react";
import { Calendar, Database, KeyRound, ScrollText, Trash2, Copy, Check, Users } from "lucide-react";

export default function OrgDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const qc = useQueryClient();
  const [newToken, setNewToken] = useState<ApiTokenCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: org } = useQuery({
    queryKey: ["organizations", id],
    queryFn: () => api.get<Organization>(`/organizations/${id}`),
  });

  const { data: tokens } = useQuery({
    queryKey: ["tokens", id],
    queryFn: () => api.get<ApiToken[]>(`/organizations/${id}/tokens`),
  });

  const createToken = useMutation({
    mutationFn: (label: string) =>
      api.post<ApiTokenCreated>(`/organizations/${id}/tokens`, { label: label || null }),
    onSuccess: (t) => {
      setNewToken(t);
      qc.invalidateQueries({ queryKey: ["tokens", id] });
    },
  });

  const revokeToken = useMutation({
    mutationFn: (tokenId: string) => api.delete(`/organizations/${id}/tokens/${tokenId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tokens", id] }),
  });

  function copyToken(raw: string) {
    navigator.clipboard.writeText(raw);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!org) return <p className="text-sm text-gray-500">Laden...</p>;

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900">{org.name}</h1>

      <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-2 text-sm">
        <Row label="KBO" value={org.kbo} />
        <Row label="Adres" value={[org.street, org.zip, org.city].filter(Boolean).join(", ") || "—"} />
        <Row label="Contactpersoon" value={org.contact_name ?? "—"} />
        <Row label="E-mail" value={org.contact_email ?? "—"} />
        <Row label="Telefoon" value={org.contact_phone ?? "—"} />
        <Row label="Taalcode" value={org.language_code} />
      </section>

      <section className="flex flex-wrap gap-2">
        <Link
          href={`/organizations/${id}/odoo-connection`}
          className="inline-flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-900 text-sm font-medium px-4 py-2.5 rounded-lg"
        >
          <Database className="w-4 h-4 text-brand-600" />
          Odoo Connectie
        </Link>
        <Link
          href={`/organizations/${id}/events`}
          className="inline-flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-900 text-sm font-medium px-4 py-2.5 rounded-lg"
        >
          <Calendar className="w-4 h-4 text-brand-600" />
          Events
        </Link>
        <Link
          href={`/organizations/${id}/participations`}
          className="inline-flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-900 text-sm font-medium px-4 py-2.5 rounded-lg"
        >
          <ScrollText className="w-4 h-4 text-brand-600" />
          Deelnames
        </Link>
        <Link
          href={`/organizations/${id}/beneficiaries`}
          className="inline-flex items-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 text-gray-900 text-sm font-medium px-4 py-2.5 rounded-lg"
        >
          <Users className="w-4 h-4 text-brand-600" />
          Begunstigden
        </Link>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-medium text-gray-900">API Tokens</h2>
          <button
            onClick={() => {
              const label = prompt("Label voor token (optioneel):") ?? "";
              createToken.mutate(label);
            }}
            className="inline-flex items-center gap-1.5 text-sm bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded-lg font-medium"
          >
            <KeyRound className="w-3.5 h-3.5" />
            Nieuw token
          </button>
        </div>

        {newToken && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm">
            <p className="font-medium text-amber-800 mb-2">Token aangemaakt — sla dit op, het wordt niet opnieuw getoond.</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 bg-white border border-amber-200 rounded px-3 py-2 text-xs break-all font-mono">
                {newToken.raw_token}
              </code>
              <button onClick={() => copyToken(newToken.raw_token)}
                className="p-2 rounded-lg hover:bg-amber-100 text-amber-700 flex-shrink-0">
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
            <button onClick={() => setNewToken(null)} className="mt-2 text-xs text-amber-600 hover:underline">
              Sluiten
            </button>
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {tokens && tokens.length === 0 && (
            <p className="px-4 py-3 text-sm text-gray-500">Geen tokens</p>
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
                  onClick={() => { if (confirm("Token intrekken?")) revokeToken.mutate(t.id); }}
                  className="p-1.5 rounded-lg text-red-500 hover:bg-red-50 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex gap-4">
      <span className="w-32 text-gray-500 flex-shrink-0">{label}</span>
      <span className="text-gray-900">{value}</span>
    </div>
  );
}
