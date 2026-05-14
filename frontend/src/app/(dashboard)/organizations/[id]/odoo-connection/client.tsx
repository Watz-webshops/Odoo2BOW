"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Copy, Check, Database, RefreshCw, Trash2, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { useRouteSegment } from "@/lib/route";

type Connection = {
  id: string;
  url: string;
  database: string;
  username: string;
  api_key_masked: string;
  bootstrap_completed: boolean;
  is_active: boolean;
  last_sync_at: string | null;
  webhook_url: string;
};

type ConnectionWithSecret = Connection & { webhook_secret: string };

type TestResult = {
  connection: "ok" | "failed";
  message?: string;
  questions_found: string[];
  questions_missing: string[];
  registrations_count: number;
};

type SyncStatus = {
  bootstrap_completed: boolean;
  last_sync_at: string | null;
  counts: { events: number; partners: number; registrations: number };
  recent_syncs: Array<{
    id: string;
    sync_type: string;
    status: string;
    events_synced: number;
    registrations_synced: number;
    partners_synced: number;
    deleted_count: number;
    error_detail: string | null;
    started_at: string;
    completed_at: string | null;
  }>;
};

export function AdminOdooConnectionPageClient() {
  const orgId = useRouteSegment("/organizations");
  const apiBase = `/organizations/${orgId}`;

  const qc = useQueryClient();
  const [secretShown, setSecretShown] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [form, setForm] = useState({ url: "", database: "", username: "", api_key: "" });

  const { data: conn } = useQuery({
    queryKey: ["org", orgId, "odoo-connection"],
    queryFn: () => api.get<Connection | null>(`${apiBase}/odoo-connection`),
  });

  useEffect(() => {
    if (conn) {
      setForm({
        url: conn.url,
        database: conn.database,
        username: conn.username,
        api_key: "",
      });
    }
  }, [conn]);

  const { data: syncStatus } = useQuery({
    queryKey: ["org", orgId, "sync-status"],
    queryFn: () => api.get<SyncStatus>(`${apiBase}/sync-status`),
    refetchInterval: 5000,
  });

  const save = useMutation({
    mutationFn: () => api.put<ConnectionWithSecret>(`${apiBase}/odoo-connection`, form),
    onSuccess: (c) => {
      setSecretShown(c.webhook_secret);
      qc.invalidateQueries({ queryKey: ["org", orgId, "odoo-connection"] });
      qc.invalidateQueries({ queryKey: ["org", orgId, "sync-status"] });
    },
  });

  const test = useMutation({
    mutationFn: () => api.post<TestResult>(`${apiBase}/odoo-connection/test`, {}),
    onSuccess: (r) => setTestResult(r),
  });

  const bootstrap = useMutation({
    mutationFn: () => api.post(`${apiBase}/odoo-connection/bootstrap`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org", orgId, "sync-status"] }),
  });

  const resync = useMutation({
    mutationFn: () => api.post(`${apiBase}/odoo-connection/resync`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org", orgId, "sync-status"] }),
  });

  const del = useMutation({
    mutationFn: () => api.delete(`${apiBase}/odoo-connection`),
    onSuccess: () => {
      setSecretShown(null);
      setTestResult(null);
      setForm({ url: "", database: "", username: "", api_key: "" });
      qc.invalidateQueries({ queryKey: ["org", orgId, "odoo-connection"] });
      qc.invalidateQueries({ queryKey: ["org", orgId, "sync-status"] });
    },
  });

  function copy(value: string, key: string) {
    navigator.clipboard.writeText(value);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  }

  const snippet = (webhookUrl: string, secret: string) => `# In Odoo: Settings → Technical → Server Actions → Nieuw
# Model: event.registration  (ook duplicate maken voor event.event en res.partner)
# Type: Execute Python Code

import requests, hmac, hashlib, json
WEBHOOK_URL = "${webhookUrl}"
SECRET = "${secret}"
ACTION = "write"  # 'create' | 'write' | 'unlink' afhankelijk van trigger
for record in records:
    payload = {"model": record._name, "id": record.id, "action": ACTION}
    body = json.dumps(payload).encode()
    sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    requests.post(WEBHOOK_URL, data=body, headers={
        "X-Odoo2BOW-Signature": "sha256=" + sig,
        "Content-Type": "application/json",
    }, timeout=5)

# Koppel deze Server Action aan een Automation Rule die triggert bij Create/Write/Unlink.`;

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3 text-sm">
        <Link href={`/organizations/${orgId}`} className="text-brand-600 hover:underline inline-flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          Terug naar organisatie
        </Link>
      </div>

      <h1 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
        <Database className="w-5 h-5 text-brand-600" />
        Odoo Connectie (admin)
      </h1>

      <form
        onSubmit={(e) => { e.preventDefault(); save.mutate(); }}
        className="bg-white rounded-xl border border-gray-200 p-5 space-y-4"
      >
        <h2 className="font-medium text-gray-900">Verbinding configureren</h2>

        <Field label="Odoo URL" placeholder="https://uwbedrijf.odoo.com"
          value={form.url} onChange={(v) => setForm({ ...form, url: v })} required />
        <Field label="Database naam" placeholder="uwbedrijf"
          value={form.database} onChange={(v) => setForm({ ...form, database: v })} required />
        <Field label="Username (e-mail)" placeholder="user@uwbedrijf.be"
          value={form.username} onChange={(v) => setForm({ ...form, username: v })} required />
        <div>
          <Field label="API Key"
            placeholder={conn ? "Laat leeg om huidige sleutel te behouden" : "Genereer in Odoo: Settings → Users → API Keys"}
            value={form.api_key} onChange={(v) => setForm({ ...form, api_key: v })} type="password" required={!conn} />
          {conn && (
            <p className="mt-1 text-xs text-gray-500">
              Huidige sleutel: <code className="font-mono text-gray-700">{conn.api_key_masked}</code>
            </p>
          )}
        </div>

        <div className="flex gap-2">
          <button type="submit" disabled={save.isPending}
            className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50">
            {save.isPending ? "Opslaan..." : (conn ? "Bijwerken" : "Opslaan")}
          </button>
          {conn && (
            <button type="button" onClick={() => test.mutate()} disabled={test.isPending}
              className="bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50">
              {test.isPending ? "Testen..." : "Test verbinding"}
            </button>
          )}
        </div>
      </form>

      {testResult && (
        <div className={`rounded-xl border p-5 text-sm ${
          testResult.connection === "ok" ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
        }`}>
          <p className={`font-medium mb-2 ${testResult.connection === "ok" ? "text-green-800" : "text-red-800"}`}>
            {testResult.connection === "ok"
              ? `✓ Verbinding succesvol — ${testResult.registrations_count} registraties in Odoo`
              : `✗ Verbinding mislukt: ${testResult.message}`}
          </p>
          {testResult.connection === "ok" && (
            <>
              <p className="text-green-800 font-medium mt-3">Vragen gevonden:</p>
              <ul className="list-disc ml-5 text-green-700 text-xs">
                {testResult.questions_found.map((q) => <li key={q}>{q}</li>)}
              </ul>
              {testResult.questions_missing.length > 0 && (
                <>
                  <p className="text-amber-800 font-medium mt-3">Ontbrekende vragen:</p>
                  <ul className="list-disc ml-5 text-amber-700 text-xs">
                    {testResult.questions_missing.map((q) => <li key={q}>{q} (vereist)</li>)}
                  </ul>
                </>
              )}
            </>
          )}
        </div>
      )}

      {secretShown && conn && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 space-y-3 text-sm">
          <p className="font-medium text-amber-800">
            Webhook secret — sla nu op, wordt niet opnieuw getoond.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-white border border-amber-200 rounded px-3 py-2 text-xs break-all font-mono">
              {secretShown}
            </code>
            <button onClick={() => copy(secretShown, "secret")}
              className="p-2 rounded-lg hover:bg-amber-100 text-amber-700">
              {copiedKey === "secret" ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>

          <p className="font-medium text-amber-800 mt-2">Webhook URL:</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-white border border-amber-200 rounded px-3 py-2 text-xs break-all font-mono">
              {conn.webhook_url}
            </code>
            <button onClick={() => copy(conn.webhook_url, "url")}
              className="p-2 rounded-lg hover:bg-amber-100 text-amber-700">
              {copiedKey === "url" ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>

          <p className="font-medium text-amber-800 mt-2">Odoo Server Action snippet:</p>
          <div className="relative">
            <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 text-xs overflow-auto max-h-72">
{snippet(conn.webhook_url, secretShown)}
            </pre>
            <button onClick={() => copy(snippet(conn.webhook_url, secretShown), "snippet")}
              className="absolute top-2 right-2 p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200">
              {copiedKey === "snippet" ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>

          <button onClick={() => setSecretShown(null)} className="text-xs text-amber-700 hover:underline">
            Sluiten
          </button>
        </div>
      )}

      {conn && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h2 className="font-medium text-gray-900">Synchronisatie</h2>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => bootstrap.mutate()} disabled={bootstrap.isPending}
              className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-3 py-2 rounded-lg disabled:opacity-50">
              <Zap className="w-4 h-4" />
              {conn.bootstrap_completed ? "Re-bootstrap" : "Initial bootstrap"}
            </button>
            <button onClick={() => resync.mutate()} disabled={resync.isPending}
              className="inline-flex items-center gap-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium px-3 py-2 rounded-lg disabled:opacity-50">
              <RefreshCw className="w-4 h-4" />
              Volledige resync
            </button>
            <button onClick={() => { if (confirm("Verbinding verwijderen + alle gesyncde data?")) del.mutate(); }}
              className="inline-flex items-center gap-1.5 ml-auto text-red-600 hover:bg-red-50 text-sm font-medium px-3 py-2 rounded-lg">
              <Trash2 className="w-4 h-4" />
              Verbinding verwijderen
            </button>
          </div>

          {syncStatus && (
            <div className="grid grid-cols-3 gap-4 text-sm pt-2 border-t border-gray-100">
              <Stat label="Events" value={syncStatus.counts.events} />
              <Stat label="Inschrijvingen" value={syncStatus.counts.registrations} />
              <Stat label="Partners" value={syncStatus.counts.partners} />
            </div>
          )}
        </div>
      )}

      {syncStatus && syncStatus.recent_syncs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-200">
            <h2 className="font-medium text-gray-900">Recente sync activiteit</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-600">Type</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-600">Status</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-600">Events</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-600">Regs</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-600">Partners</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-600">Verwijderd</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-600">Tijdstip</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {syncStatus.recent_syncs.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-2 text-xs text-gray-700">{s.sync_type}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      s.status === "completed" ? "bg-green-100 text-green-700" :
                      s.status === "failed" ? "bg-red-100 text-red-700" :
                      "bg-blue-100 text-blue-700"
                    }`}>{s.status}</span>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-600">{s.events_synced}</td>
                  <td className="px-4 py-2 text-xs text-gray-600">{s.registrations_synced}</td>
                  <td className="px-4 py-2 text-xs text-gray-600">{s.partners_synced}</td>
                  <td className="px-4 py-2 text-xs text-gray-600">{s.deleted_count}</td>
                  <td className="px-4 py-2 text-xs text-gray-500">
                    {new Date(s.started_at).toLocaleString("nl-BE")}
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

function Field({ label, value, onChange, type = "text", placeholder, required }: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string; required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder} required={required}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}
