"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, AlertTriangle, CheckCircle2, ChevronRight, FileWarning, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { centsToEur, cn } from "@/lib/utils";
import type { ExportPreview, FichePreview, PeriodPreview } from "@/types/preview";

interface Props {
  /** Base path naar de preview-endpoint, bv. `/me/exports/preview` of `/organizations/{id}/exports/preview`. */
  previewPath: string;
  /** Base path naar de echte XML-genereer-endpoint (POST), bv. `/me/exports/from-local`. */
  generatePath: string;
  /** Heading voor de pagina. */
  title: string;
}

export function ExportPreviewView({ previewPath, generatePath, title }: Props) {
  const qc = useQueryClient();
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear - 1);
  const [testMode, setTestMode] = useState(false);
  const [selectedSeq, setSelectedSeq] = useState<number | null>(null);

  const { data, isFetching, error, refetch } = useQuery<ExportPreview>({
    queryKey: [previewPath, year, testMode],
    queryFn: () =>
      api.get<ExportPreview>(`${previewPath}?income_year=${year}&test_mode=${testMode}`),
    enabled: false,
  });

  const generate = useMutation({
    mutationFn: () => api.post<{ export_id: string }>(generatePath, { income_year: year }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me", "exports"] });
      qc.invalidateQueries({ queryKey: ["admin", "exports"] });
    },
  });

  const selectedFiche = data?.fiches.find((f) => f.seq === selectedSeq) ?? null;

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-gray-900">{title}</h1>

      {/* Controls */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Inkomstenjaar</label>
          <select
            value={year}
            onChange={(e) => setYear(parseInt(e.target.value, 10))}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {[currentYear - 2, currentYear - 1, currentYear, currentYear + 1].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer py-2">
          <input
            type="checkbox"
            checked={testMode}
            onChange={(e) => setTestMode(e.target.checked)}
            className="rounded border-gray-300"
          />
          Test-modus (BCTEST)
        </label>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="ml-auto px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          {isFetching ? "Laden..." : "Voorvertonen"}
        </button>
        <button
          onClick={() => generate.mutate()}
          disabled={!data || data.fiches.length === 0 || generate.isPending}
          className="inline-flex items-center gap-1.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50"
        >
          <Zap className="w-4 h-4" />
          {generate.isPending ? "Bezig..." : "Genereer XML"}
        </button>
      </div>

      {error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          Fout bij het laden van de preview.
        </div>
      ) : null}

      {generate.isSuccess ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800">
          Export gestart. ID: <code className="font-mono">{generate.data?.export_id}</code>
        </div>
      ) : null}

      {!data ? (
        <p className="text-sm text-gray-500">Klik op "Voorvertonen" om de data voor jaar {year} te laden.</p>
      ) : (
        <>
          <SummaryCard preview={data} />
          <HeaderCard preview={data} />
          <FicheTable
            preview={data}
            selectedSeq={selectedSeq}
            onSelect={setSelectedSeq}
          />
          {selectedFiche && (
            <FicheDetail
              fiche={selectedFiche}
              onClose={() => setSelectedSeq(null)}
            />
          )}
          <TrailerCard preview={data} />
        </>
      )}
    </div>
  );
}

function SummaryCard({ preview }: { preview: ExportPreview }) {
  const s = preview.summary;
  const hasErrors = s.errors.length > 0;
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <Stat label="Fiches" value={s.fiche_count} />
        <Stat label="Totaalbedrag" value={centsToEur(s.total_amount_cents)} />
        <Stat label="Opvangdagen" value={s.total_xml_days} />
        <Stat label="Overgeslagen" value={s.skipped_count} />
      </div>
      {hasErrors && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-red-800 mb-1">
            <AlertCircle className="w-4 h-4" />
            Fouten — XML kan niet gegenereerd worden
          </div>
          <ul className="text-xs text-red-700 list-disc list-inside space-y-0.5">
            {s.errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
      {s.invalid_registrations.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-orange-900">
            <FileWarning className="w-4 h-4" />
            {s.invalid_registrations.length} ongeldige inschrijving
            {s.invalid_registrations.length === 1 ? "" : "en"} — corrigeer in Odoo
          </div>
          <ul className="text-xs text-orange-900 space-y-1.5">
            {s.invalid_registrations.map((r) => {
              const childName = [r.child_first_name, r.child_last_name].filter(Boolean).join(" ");
              return (
                <li key={r.registration_odoo_id} className="border-l-2 border-orange-300 pl-2">
                  <div className="font-medium">
                    {r.event_name || "(zonder naam)"} · {r.partner_name || "(zonder ouder)"}
                    {childName ? ` · kind ${childName}` : ""}
                  </div>
                  <div className="text-orange-700">{r.reasons.join(" · ")}</div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
      {s.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-800 mb-1">
            <AlertTriangle className="w-4 h-4" />
            {s.warnings.length} waarschuwing{s.warnings.length === 1 ? "" : "en"}
          </div>
          <ul className="text-xs text-amber-700 list-disc list-inside space-y-0.5">
            {s.warnings.slice(0, 8).map((w, i) => (
              <li key={i}>{w.message}{w.child_rrn ? ` (kind ${w.child_rrn})` : ""}</li>
            ))}
            {s.warnings.length > 8 && <li>… en {s.warnings.length - 8} meer</li>}
          </ul>
        </div>
      )}
      {s.organization_missing.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
          <div className="font-medium mb-1">Optionele organisatie-velden ontbreken:</div>
          {s.organization_missing.map((m) => <span key={m} className="inline-block mr-2">• {m}</span>)}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-semibold text-gray-900">{value}</div>
    </div>
  );
}

function HeaderCard({ preview }: { preview: ExportPreview }) {
  const [open, setOpen] = useState(false);
  const v = preview.verzending;
  const a = preview.aangifte;
  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="bg-white rounded-xl border border-gray-200"
    >
      <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-gray-900 flex items-center gap-2">
        <ChevronRight className={cn("w-4 h-4 transition-transform", open && "rotate-90")} />
        Verzending- &amp; aangifte-header (v00xx / a10xx)
      </summary>
      <div className="px-4 pb-4 grid md:grid-cols-2 gap-4 text-xs">
        <FieldGroup title="Verzending">
          <Field k="v0002_inkomstenjaar" v={v.v0002_inkomstenjaar} />
          <Field k="v0010_bestandtype" v={v.v0010_bestandtype} />
          <Field k="v0011_aanmaakdatum" v={v.v0011_aanmaakdatum} />
          <Field k="v0014_naam" v={v.v0014_naam} />
          <Field k="v0015_adres" v={v.v0015_adres} />
          <Field k="v0016_postcode" v={v.v0016_postcode} />
          <Field k="v0017_gemeente" v={v.v0017_gemeente} />
          <Field k="v0018_telefoonnummer" v={v.v0018_telefoonnummer} />
          <Field k="v0021_contactpersoon" v={v.v0021_contactpersoon} />
          <Field k="v0022_taalcode" v={v.v0022_taalcode} />
          <Field k="v0023_emailadres" v={v.v0023_emailadres} />
          <Field k="v0024_nationaalnr" v={v.v0024_nationaalnr} />
          <Field k="v0028_landwoonplaats" v={v.v0028_landwoonplaats} />
        </FieldGroup>
        <FieldGroup title="Aangifte">
          <Field k="a1005_registratienummer" v={a.a1005_registratienummer} />
          <Field k="a1011_naamnl1" v={a.a1011_naamnl1} />
          <Field k="a1013_adresnl" v={a.a1013_adresnl} />
          <Field k="a1015_gemeente" v={a.a1015_gemeente} />
          <Field k="a1020_taalcode" v={a.a1020_taalcode} />
          <Field k="a1027_naamfr1" v={a.a1027_naamfr1} optional />
          <Field k="a1029_adresfr" v={a.a1029_adresfr} optional />
          <Field k="a1030_gemeentefr" v={a.a1030_gemeentefr} optional />
          <Field k="a1032_naamde1" v={a.a1032_naamde1} optional />
          <Field k="a1034_adresde" v={a.a1034_adresde} optional />
          <Field k="a1035_gemeentede" v={a.a1035_gemeentede} optional />
        </FieldGroup>
      </div>
    </details>
  );
}

function FicheTable({
  preview, selectedSeq, onSelect,
}: {
  preview: ExportPreview;
  selectedSeq: number | null;
  onSelect: (seq: number) => void;
}) {
  if (preview.fiches.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 text-center text-sm text-gray-400">
        Geen fiches voor jaar {preview.income_year}.
      </div>
    );
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200 text-xs">
          <tr>
            <th className="text-left px-3 py-2 font-medium text-gray-600 w-12">#</th>
            <th className="text-left px-3 py-2 font-medium text-gray-600">Ouder</th>
            <th className="text-left px-3 py-2 font-medium text-gray-600">Kind</th>
            <th className="text-left px-3 py-2 font-medium text-gray-600">Periode</th>
            <th className="text-right px-3 py-2 font-medium text-gray-600">Dagen</th>
            <th className="text-right px-3 py-2 font-medium text-gray-600">Bedrag</th>
            <th className="px-3 py-2 w-10" />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {preview.fiches.map((f) => {
            const xmlDays = f.period1.xml_days + (f.period2?.xml_days ?? 0);
            const isSelected = f.seq === selectedSeq;
            const hasIssues = f.missing_fields.length > 0 || f.warnings.length > 0;
            return (
              <tr
                key={f.seq}
                onClick={() => onSelect(f.seq)}
                className={cn(
                  "cursor-pointer hover:bg-gray-50",
                  isSelected && "bg-brand-50",
                )}
              >
                <td className="px-3 py-2 text-gray-500">{f.seq}</td>
                <td className="px-3 py-2 text-gray-900">
                  {f.f2114_voornamen} {f.f2013_naam}
                  <div className="text-xs text-gray-500 font-mono">{f.f2011_nationaalnr}</div>
                </td>
                <td className="px-3 py-2 text-gray-900">
                  {f.f86_2107_childfirstname} {f.f86_2106_childname}
                  <div className="text-xs text-gray-500 font-mono">{f.f86_2153_nnchild}</div>
                </td>
                <td className="px-3 py-2 text-xs text-gray-700">
                  {f.period1.begindate} → {f.period1.enddate}
                  {f.period2 && (
                    <div>{f.period2.begindate} → {f.period2.enddate}</div>
                  )}
                </td>
                <td className="px-3 py-2 text-right text-gray-700">{xmlDays}</td>
                <td className="px-3 py-2 text-right text-gray-900 font-medium">
                  {centsToEur(f.f86_2064_totalamount)}
                </td>
                <td className="px-3 py-2 text-center">
                  {f.missing_fields.length > 0 ? (
                    <AlertCircle className="w-4 h-4 text-red-500 inline" />
                  ) : f.warnings.length > 0 ? (
                    <AlertTriangle className="w-4 h-4 text-amber-500 inline" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-green-500 inline" />
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function FicheDetail({ fiche, onClose }: { fiche: FichePreview; onClose: () => void }) {
  return (
    <div className="bg-white rounded-xl border border-brand-200 shadow-sm p-5 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-semibold text-gray-900">Fiche {fiche.seq} — alle XML-velden</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            ref: <code className="font-mono">{fiche.f2010_referentie}</code>
          </p>
        </div>
        <button onClick={onClose} className="text-sm text-gray-500 hover:underline">Sluiten</button>
      </div>

      {fiche.missing_fields.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
          <FileWarning className="w-4 h-4 inline mr-1" />
          Ontbrekende velden: {fiche.missing_fields.join(", ")}
        </div>
      )}
      {fiche.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
          {fiche.warnings.map((w, i) => <div key={i}>• {w}</div>)}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <FieldGroup title="Identificatie">
          <Field k="f2008_typefiche" v={fiche.f2008_typefiche} />
          <Field k="f2009_volgnummer" v={fiche.f2009_volgnummer} />
          <Field k="f2010_referentie" v={fiche.f2010_referentie} />
        </FieldGroup>
        <FieldGroup title="Ouder">
          <Field k="f2011_nationaalnr" v={fiche.f2011_nationaalnr} />
          <Field k="f2013_naam" v={fiche.f2013_naam} />
          <Field k="f2114_voornamen" v={fiche.f2114_voornamen} />
          <Field k="f2015_adres" v={fiche.f2015_adres} />
          <Field k="f2016_postcodebelgisch" v={fiche.f2016_postcodebelgisch} />
          <Field k="f2017_gemeente" v={fiche.f2017_gemeente} />
        </FieldGroup>
        <FieldGroup title="Kind">
          <Field k="f86_2153_nnchild" v={fiche.f86_2153_nnchild} />
          <Field k="f86_2106_childname" v={fiche.f86_2106_childname} />
          <Field k="f86_2107_childfirstname" v={fiche.f86_2107_childfirstname} />
          <Field k="f86_2163_childbirthdate" v={fiche.f86_2163_childbirthdate} />
          <Field k="f86_2102_childaddress" v={fiche.f86_2102_childaddress} />
          <Field k="f86_2139_childpostnr" v={fiche.f86_2139_childpostnr} />
          <Field k="f86_2140_childmunicipality" v={fiche.f86_2140_childmunicipality} />
        </FieldGroup>
        <FieldGroup title="Totalen">
          <Field k="f86_2059_totaalcontrole" v={centsToEur(fiche.f86_2059_totaalcontrole)} />
          <Field k="f86_2064_totalamount" v={centsToEur(fiche.f86_2064_totalamount)} />
        </FieldGroup>
      </div>

      <PeriodCard label="Periode 1 (f86_2055/2056/2060/2110/2111)" period={fiche.period1} />
      {fiche.period2 ? (
        <PeriodCard label="Periode 2 (f86_2093/2144/2061/2113/2115)" period={fiche.period2} />
      ) : (
        <div className="text-xs text-gray-400 italic">Geen tweede periode (1 cluster gedetecteerd).</div>
      )}
    </div>
  );
}

function PeriodCard({ label, period }: { label: string; period: PeriodPreview }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="text-xs font-medium text-gray-700 mb-2">{label}</div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1 text-xs">
        <Field k="begindate" v={period.begindate} />
        <Field k="enddate" v={period.enddate} />
        <Field k="amount" v={centsToEur(period.amount_cents)} />
        <Field k="half_days (intern)" v={period.half_days} />
        <Field k="xml_days (numberofday)" v={period.xml_days} />
        <Field k="dailytariff" v={centsToEur(period.daily_tariff_cents)} />
      </div>
      <p className="text-xs text-gray-500 mt-2 italic">
        {period.half_days} halve dagen → afgerond naar {period.xml_days} dag{period.xml_days === 1 ? "" : "en"} voor f86_2110/2113.
      </p>
    </div>
  );
}

function TrailerCard({ preview }: { preview: ExportPreview }) {
  const t = preview.trailer;
  return (
    <details className="bg-white rounded-xl border border-gray-200">
      <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-gray-700">
        Controle-totalen (r8 + r9)
      </summary>
      <div className="px-4 pb-4 grid md:grid-cols-2 gap-4 text-xs">
        <FieldGroup title="r8 (aangifte)">
          <Field k="r8010_aantalrecords" v={t.r8010_aantalrecords} />
          <Field k="r8011_controletotaal" v={t.r8011_controletotaal} />
          <Field k="r8012_controletotaal" v={t.r8012_controletotaal} />
        </FieldGroup>
        <FieldGroup title="r9 (verzending)">
          <Field k="r9010_aantallogbestanden" v={t.r9010_aantallogbestanden} />
          <Field k="r9011_totaalaantalrecords" v={t.r9011_totaalaantalrecords} />
          <Field k="r9012_controletotaal" v={t.r9012_controletotaal} />
          <Field k="r9013_controletotaal" v={t.r9013_controletotaal} />
        </FieldGroup>
      </div>
    </details>
  );
}

function FieldGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase text-gray-500 mb-1">{title}</h3>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function Field({ k, v, optional }: { k: string; v: string | number | null | undefined; optional?: boolean }) {
  const empty = v === null || v === undefined || v === "";
  return (
    <div className="flex gap-2">
      <span className="text-gray-500 font-mono">{k}</span>
      <span className={cn("text-gray-900 truncate", empty && (optional ? "text-gray-400 italic" : "text-red-600"))}>
        {empty ? (optional ? "(niet ingevuld)" : "—") : v}
      </span>
    </div>
  );
}
