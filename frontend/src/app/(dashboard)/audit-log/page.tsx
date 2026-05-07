"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type AuditEntry = {
  id: string;
  actor_type: string;
  actor_email: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
};

const ACTION_COLORS: Record<string, string> = {
  "admin.create": "bg-blue-100 text-blue-700",
  "admin.delete": "bg-red-100 text-red-700",
  "admin.password_reset": "bg-amber-100 text-amber-700",
  "user.create": "bg-blue-100 text-blue-700",
  "user.delete": "bg-red-100 text-red-700",
  "user.password_reset": "bg-amber-100 text-amber-700",
  "org.create": "bg-green-100 text-green-700",
  "org.update": "bg-gray-100 text-gray-700",
  "token.create": "bg-purple-100 text-purple-700",
  "token.revoke": "bg-red-100 text-red-700",
  "export.create": "bg-indigo-100 text-indigo-700",
};

export default function AuditLogPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["audit-log"],
    queryFn: () => api.get<AuditEntry[]>("/audit-log?limit=200"),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-gray-900">Audit log</h1>

      {isLoading && <p className="text-sm text-gray-500">Laden...</p>}

      {data && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tijdstip</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Actor</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Actie</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Target</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs text-gray-500 font-mono whitespace-nowrap">
                    {new Date(e.created_at).toLocaleString("nl-BE")}
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    <span className="text-xs text-gray-500">{e.actor_type}</span>
                    {e.actor_email && <div>{e.actor_email}</div>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ACTION_COLORS[e.action] ?? "bg-gray-100 text-gray-700"}`}>
                      {e.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600 font-mono">
                    {e.target_type && (
                      <>
                        {e.target_type}
                        {e.target_id && <span className="text-gray-400"> · {e.target_id.slice(0, 12)}</span>}
                      </>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {e.details && (
                      <code className="font-mono">{JSON.stringify(e.details)}</code>
                    )}
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr><td colSpan={5} className="text-center py-6 text-gray-400">Geen activiteit</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
