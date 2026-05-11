"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ChevronRight, Save } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Organization, OrganizationUpdate } from "@/types/organization";

interface Props {
  org: Organization;
  /** Endpoint voor PUT — default `/organizations/{id}`. Self-service: `/me/organization`. */
  endpoint?: string;
  onSaved?: () => void;
}

interface FormState {
  name_fr: string;
  street_fr: string;
  city_fr: string;
  name_de: string;
  street_de: string;
  city_de: string;
  cert_validity_start: string;
  cert_validity_end: string;
}

function fromOrg(org: Organization): FormState {
  return {
    name_fr: org.name_fr ?? "",
    street_fr: org.street_fr ?? "",
    city_fr: org.city_fr ?? "",
    name_de: org.name_de ?? "",
    street_de: org.street_de ?? "",
    city_de: org.city_de ?? "",
    cert_validity_start: org.cert_validity_start ?? "",
    cert_validity_end: org.cert_validity_end ?? "",
  };
}

function toPayload(s: FormState): OrganizationUpdate {
  const v = (x: string) => (x.trim() === "" ? null : x);
  return {
    name_fr: v(s.name_fr),
    street_fr: v(s.street_fr),
    city_fr: v(s.city_fr),
    name_de: v(s.name_de),
    street_de: v(s.street_de),
    city_de: v(s.city_de),
    cert_validity_start: v(s.cert_validity_start),
    cert_validity_end: v(s.cert_validity_end),
  };
}

export function BowFieldsEditor({ org, endpoint, onSaved }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(() => fromOrg(org));
  const path = endpoint ?? `/organizations/${org.id}`;

  const save = useMutation({
    mutationFn: (data: OrganizationUpdate) => api.put<Organization>(path, data),
    onSuccess: () => onSaved?.(),
  });

  function update<K extends keyof FormState>(key: K, value: string) {
    setForm((s) => ({ ...s, [key]: value }));
  }

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="bg-white rounded-xl border border-gray-200"
    >
      <summary className="cursor-pointer px-5 py-4 text-sm font-medium text-gray-900 flex items-center gap-2">
        <ChevronRight className={cn("w-4 h-4 transition-transform", open && "rotate-90")} />
        BOW-velden (FR/DE benamingen + certificeringsgeldigheid)
        <span className="ml-auto text-xs font-normal text-gray-500">
          Optioneel — wordt enkel uitgeschreven in de XML wanneer ingevuld
        </span>
      </summary>

      <div className="px-5 pb-5 space-y-5 text-sm">
        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold uppercase text-gray-500">Frans (a1027 / a1029 / a1030)</legend>
          <Input label="Naam (FR)" value={form.name_fr} onChange={(v) => update("name_fr", v)} placeholder="SPF Finances" />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Adres (FR)" value={form.street_fr} onChange={(v) => update("street_fr", v)} placeholder="Rue de test, 10" />
            <Input label="Gemeente (FR)" value={form.city_fr} onChange={(v) => update("city_fr", v)} placeholder="Bruxelles" />
          </div>
        </fieldset>

        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold uppercase text-gray-500">Duits (a1032 / a1034 / a1035)</legend>
          <Input label="Naam (DE)" value={form.name_de} onChange={(v) => update("name_de", v)} placeholder="FÖD Finanzen" />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Adres (DE)" value={form.street_de} onChange={(v) => update("street_de", v)} placeholder="Teststrasse, 1" />
            <Input label="Gemeente (DE)" value={form.city_de} onChange={(v) => update("city_de", v)} placeholder="Brüssel" />
          </div>
        </fieldset>

        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold uppercase text-gray-500">
            Certificeringsgeldigheid (f86_2164 / f86_2171)
          </legend>
          <p className="text-xs text-gray-500">
            Wanneer ingevuld, worden deze datums op elke fiche in de XML toegevoegd.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Geldig vanaf" type="date" value={form.cert_validity_start}
              onChange={(v) => update("cert_validity_start", v)} />
            <Input label="Geldig tot" type="date" value={form.cert_validity_end}
              onChange={(v) => update("cert_validity_end", v)} />
          </div>
        </fieldset>

        {save.error ? (
          <p className="text-xs text-red-600">Fout bij opslaan.</p>
        ) : save.isSuccess ? (
          <p className="text-xs text-green-700">Opgeslagen.</p>
        ) : null}

        <div className="flex justify-end">
          <button
            onClick={() => save.mutate(toPayload(form))}
            disabled={save.isPending}
            className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {save.isPending ? "Opslaan..." : "Opslaan"}
          </button>
        </div>
      </div>
    </details>
  );
}

function Input({
  label, value, onChange, type = "text", placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange((e.target as HTMLInputElement).value)}
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      />
    </div>
  );
}
