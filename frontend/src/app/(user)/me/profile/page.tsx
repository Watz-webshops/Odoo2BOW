"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { getSession } from "@/lib/auth";
import type { Organization } from "@/types/organization";

export default function UserProfilePage() {
  const session = getSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: org } = useQuery({
    queryKey: ["me", "organization"],
    queryFn: () => api.get<Organization>("/me/organization"),
  });

  const change = useMutation({
    mutationFn: () => api.post("/auth/me/password", { current_password: current, new_password: next }),
    onSuccess: () => {
      setSuccess(true);
      setError(null);
      setCurrent(""); setNext(""); setConfirm("");
      setTimeout(() => setSuccess(false), 3000);
    },
    onError: (e: any) => setError(e?.body?.detail ?? "Fout bij wijzigen wachtwoord"),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (next !== confirm) return setError("Nieuwe wachtwoorden komen niet overeen");
    if (next.length < 8) return setError("Min. 8 tekens");
    change.mutate();
  }

  return (
    <div className="space-y-5 max-w-md">
      <h1 className="text-xl font-semibold text-gray-900">Profiel</h1>

      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-2 text-sm">
        <div className="flex gap-4">
          <span className="w-32 text-gray-500">E-mail</span>
          <span className="text-gray-900">{session?.email}</span>
        </div>
        <div className="flex gap-4">
          <span className="w-32 text-gray-500">Organisatie</span>
          <span className="text-gray-900">{org?.name ?? "—"}</span>
        </div>
        <div className="flex gap-4">
          <span className="w-32 text-gray-500">KBO</span>
          <span className="text-gray-900 font-mono">{org?.kbo ?? "—"}</span>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 className="font-medium text-gray-900">Wachtwoord wijzigen</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Huidig wachtwoord</label>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nieuw wachtwoord</label>
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={8}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Bevestig nieuw wachtwoord</label>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {success && <p className="text-sm text-green-600">✓ Wachtwoord gewijzigd</p>}

        <button type="submit" disabled={change.isPending}
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50">
          {change.isPending ? "Bezig..." : "Wijzigen"}
        </button>
      </form>
    </div>
  );
}
