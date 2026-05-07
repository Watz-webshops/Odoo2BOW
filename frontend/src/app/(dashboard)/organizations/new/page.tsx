"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Organization, OrganizationCreate } from "@/types/organization";

const schema = z.object({
  kbo: z.string().min(10).max(10),
  name: z.string().min(1),
  street: z.string().optional(),
  zip: z.string().optional(),
  city: z.string().optional(),
  contact_name: z.string().optional(),
  contact_email: z.string().email().optional().or(z.literal("")),
  contact_phone: z.string().optional(),
  language_code: z.coerce.number().int().min(1).max(3).default(1),
  country_code: z.coerce.number().int().default(150),
});

type FormData = z.infer<typeof schema>;

export default function NewOrganizationPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { language_code: 1, country_code: 150 },
  });

  const mutation = useMutation({
    mutationFn: (data: OrganizationCreate) => api.post<Organization>("/organizations", data),
    onSuccess: (org) => {
      qc.invalidateQueries({ queryKey: ["organizations"] });
      router.push(`/organizations/${org.id}`);
    },
  });

  return (
    <div className="max-w-xl space-y-5">
      <h1 className="text-xl font-semibold text-gray-900">Nieuwe organisatie</h1>

      <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <Field label="KBO-nummer *" error={errors.kbo?.message}>
          <input {...register("kbo")} placeholder="0886886638" className={input()} />
        </Field>
        <Field label="Naam *" error={errors.name?.message}>
          <input {...register("name")} className={input()} />
        </Field>
        <Field label="Straat" error={errors.street?.message}>
          <input {...register("street")} className={input()} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Postcode" error={errors.zip?.message}>
            <input {...register("zip")} className={input()} />
          </Field>
          <Field label="Gemeente" error={errors.city?.message}>
            <input {...register("city")} className={input()} />
          </Field>
        </div>
        <Field label="Contactpersoon" error={errors.contact_name?.message}>
          <input {...register("contact_name")} className={input()} />
        </Field>
        <Field label="Contact e-mail" error={errors.contact_email?.message}>
          <input {...register("contact_email")} type="email" className={input()} />
        </Field>
        <Field label="Contact telefoon" error={errors.contact_phone?.message}>
          <input {...register("contact_phone")} className={input()} />
        </Field>
        <Field label="Taalcode" error={errors.language_code?.message}>
          <select {...register("language_code")} className={input()}>
            <option value={1}>Nederlands (1)</option>
            <option value={2}>Frans (2)</option>
            <option value={3}>Duits (3)</option>
          </select>
        </Field>

        {mutation.error && (
          <p className="text-sm text-red-600">Fout bij aanmaken organisatie</p>
        )}

        <div className="flex gap-3 pt-2">
          <button type="button" onClick={() => router.back()}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50">
            Annuleren
          </button>
          <button type="submit" disabled={mutation.isPending}
            className="px-4 py-2 text-sm rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium disabled:opacity-50">
            {mutation.isPending ? "Opslaan..." : "Opslaan"}
          </button>
        </div>
      </form>
    </div>
  );
}

function input() {
  return "w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500";
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}
