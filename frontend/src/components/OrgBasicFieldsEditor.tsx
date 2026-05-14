"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Pencil, Save, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Organization, OrganizationUpdate } from "@/types/organization";

interface Props {
  org: Organization;
  /** Endpoint voor PUT — default `/organizations/{id}`. Self-service: `/me/organization`. */
  endpoint?: string;
  onSaved?: () => void;
}

interface FormState {
  name: string;
  street: string;
  zip: string;
  city: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  language_code: number;
}

function fromOrg(org: Organization): FormState {
  return {
    name: org.name,
    street: org.street ?? "",
    zip: org.zip ?? "",
    city: org.city ?? "",
    contact_name: org.contact_name ?? "",
    contact_email: org.contact_email ?? "",
    contact_phone: org.contact_phone ?? "",
    language_code: org.language_code,
  };
}

function toPayload(s: FormState): OrganizationUpdate {
  const v = (x: string) => (x.trim() === "" ? null : x);
  return {
    name: s.name.trim(),
    street: v(s.street),
    zip: v(s.zip),
    city: v(s.city),
    contact_name: v(s.contact_name),
    contact_email: v(s.contact_email),
    contact_phone: v(s.contact_phone),
    language_code: s.language_code,
  };
}

export function OrgBasicFieldsEditor({ org, endpoint, onSaved }: Props) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<FormState>(() => fromOrg(org));
  const path = endpoint ?? `/organizations/${org.id}`;

  const save = useMutation({
    mutationFn: (data: OrganizationUpdate) => api.put<Organization>(path, data),
    onSuccess: () => {
      setEditing(false);
      onSaved?.();
    },
  });

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((s) => ({ ...s, [key]: value }));
  }

  function startEdit() {
    setForm(fromOrg(org));
    save.reset();
    setEditing(true);
  }

  function cancel() {
    setForm(fromOrg(org));
    save.reset();
    setEditing(false);
  }

  if (!editing) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 p-5 text-sm">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-medium text-gray-900">Organisatiegegevens</h2>
          <button
            onClick={startEdit}
            className="inline-flex items-center gap-1.5 text-xs text-brand-600 hover:underline font-medium"
          >
            <Pencil className="w-3.5 h-3.5" />
            Bewerken
          </button>
        </div>
        <div className="space-y-2">
          <Row label="KBO" value={org.kbo} />
          <Row label="Naam" value={org.name} />
          <Row label="Adres" value={[org.street, org.zip, org.city].filter(Boolean).join(", ") || "—"} />
          <Row label="Contactpersoon" value={org.contact_name ?? "—"} />
          <Row label="E-mail" value={org.contact_email ?? "—"} />
          <Row label="Telefoon" value={org.contact_phone ?? "—"} />
          <Row label="Taalcode" value={org.language_code} />
        </div>
      </section>
    );
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-5 text-sm">
      <h2 className="font-medium text-gray-900 mb-4">Organisatiegegevens bewerken</h2>

      <div className="space-y-3">
        <Row label="KBO" value={org.kbo} />
        <Input label="Naam *" value={form.name} onChange={(v) => update("name", v)} />
        <Input label="Straat" value={form.street} onChange={(v) => update("street", v)} />
        <div className="grid grid-cols-2 gap-3">
          <Input label="Postcode" value={form.zip} onChange={(v) => update("zip", v)} />
          <Input label="Gemeente" value={form.city} onChange={(v) => update("city", v)} />
        </div>
        <Input label="Contactpersoon" value={form.contact_name} onChange={(v) => update("contact_name", v)} />
        <Input label="Contact e-mail" type="email" value={form.contact_email} onChange={(v) => update("contact_email", v)} />
        <Input label="Contact telefoon" value={form.contact_phone} onChange={(v) => update("contact_phone", v)} />
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Taalcode</label>
          <select
            value={form.language_code}
            onChange={(e) => update("language_code", Number((e.target as HTMLSelectElement).value))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value={1}>Nederlands (1)</option>
            <option value={2}>Frans (2)</option>
            <option value={3}>Duits (3)</option>
          </select>
        </div>
      </div>

      {save.error && (
        <p className="text-xs text-red-600 mt-3">Fout bij opslaan.</p>
      )}

      <div className="flex justify-end gap-2 mt-4">
        <button
          onClick={cancel}
          disabled={save.isPending}
          className="inline-flex items-center gap-1.5 border border-gray-300 text-gray-700 text-sm font-medium px-4 py-2 rounded-lg hover:bg-gray-50 disabled:opacity-50"
        >
          <X className="w-4 h-4" />
          Annuleren
        </button>
        <button
          onClick={() => save.mutate(toPayload(form))}
          disabled={save.isPending || !form.name.trim()}
          className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {save.isPending ? "Opslaan..." : "Opslaan"}
        </button>
      </div>
    </section>
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

function Input({
  label, value, onChange, type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange((e.target as HTMLInputElement).value)}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  );
}
