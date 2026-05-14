export interface VerzendingHeaderPreview {
  v0002_inkomstenjaar: number;
  v0010_bestandtype: string;
  v0011_aanmaakdatum: string;
  v0014_naam: string;
  v0015_adres: string;
  v0016_postcode: string;
  v0017_gemeente: string;
  v0018_telefoonnummer: string;
  v0021_contactpersoon: string;
  v0022_taalcode: number;
  v0023_emailadres: string;
  v0024_nationaalnr: string;
  v0025_typeenvoi: number;
  v0028_landwoonplaats: number;
}

export interface AangifteHeaderPreview {
  a1002_inkomstenjaar: number;
  a1005_registratienummer: string;
  a1011_naamnl1: string;
  a1013_adresnl: string;
  a1014_postcodebelgisch: string;
  a1015_gemeente: string;
  a1016_landwoonplaats: number;
  a1020_taalcode: number;
  a1027_naamfr1: string | null;
  a1029_adresfr: string | null;
  a1030_gemeentefr: string | null;
  a1031_taalfr: number | null;
  a1032_naamde1: string | null;
  a1034_adresde: string | null;
  a1035_gemeentede: string | null;
  a1036_taalde: number | null;
}

export interface PeriodPreview {
  begindate: string;
  enddate: string;
  amount_cents: number;
  half_days: number;
  xml_days: number;
  daily_tariff_cents: number;
}

export interface FichePreview {
  seq: number;
  f2008_typefiche: string;
  f2009_volgnummer: number;
  f2010_referentie: string;
  f2011_nationaalnr: string;
  f2013_naam: string;
  f2114_voornamen: string;
  f2015_adres: string;
  f2016_postcodebelgisch: string;
  f2017_gemeente: string;
  f2018_landwoonplaats: number;
  f86_2106_childname: string;
  f86_2107_childfirstname: string;
  f86_2153_nnchild: string;
  f86_2163_childbirthdate: string;
  f86_2101_childcountry: number;
  f86_2102_childaddress: string;
  f86_2139_childpostnr: string;
  f86_2140_childmunicipality: string;
  period1: PeriodPreview;
  period2: PeriodPreview | null;
  f86_2059_totaalcontrole: number;
  f86_2064_totalamount: number;
  missing_fields: string[];
  warnings: string[];
}

export interface TrailerPreview {
  r8010_aantalrecords: number;
  r8011_controletotaal: number;
  r8012_controletotaal: number;
  r9010_aantallogbestanden: number;
  r9011_totaalaantalrecords: number;
  r9012_controletotaal: number;
  r9013_controletotaal: number;
}

export interface PreviewSummaryWarning {
  type: string;
  parent_rrn?: string;
  child_rrn?: string;
  message: string;
}

export interface InvalidRegistration {
  registration_odoo_id: number;
  event_name: string;
  event_date_begin: string | null;
  event_date_end: string | null;
  partner_name: string;
  parent_rrn: string | null;
  child_first_name: string | null;
  child_last_name: string | null;
  child_rrn: string | null;
  reasons: string[];
}

export interface PreviewSummary {
  fiche_count: number;
  total_amount_cents: number;
  total_xml_days: number;
  skipped_count: number;
  warnings: PreviewSummaryWarning[];
  errors: string[];
  organization_missing: string[];
  invalid_registrations: InvalidRegistration[];
}

export interface ExportPreview {
  income_year: number;
  test_mode: boolean;
  verzending: VerzendingHeaderPreview;
  aangifte: AangifteHeaderPreview;
  fiches: FichePreview[];
  trailer: TrailerPreview;
  summary: PreviewSummary;
}
