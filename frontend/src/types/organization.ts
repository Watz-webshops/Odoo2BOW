export interface Organization {
  id: string;
  kbo: string;
  name: string;
  street: string | null;
  zip: string | null;
  city: string | null;
  country_code: number;
  language_code: number;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  name_fr: string | null;
  street_fr: string | null;
  city_fr: string | null;
  name_de: string | null;
  street_de: string | null;
  city_de: string | null;
  cert_validity_start: string | null;
  cert_validity_end: string | null;
  created_at: string;
}

export interface OrganizationCreate {
  kbo: string;
  name: string;
  street?: string;
  zip?: string;
  city?: string;
  country_code?: number;
  language_code?: number;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  name_fr?: string | null;
  street_fr?: string | null;
  city_fr?: string | null;
  name_de?: string | null;
  street_de?: string | null;
  city_de?: string | null;
  cert_validity_start?: string | null;
  cert_validity_end?: string | null;
}

export type OrganizationUpdate = Partial<OrganizationCreate> & {
  name?: string;
};

export interface ApiToken {
  id: string;
  org_id: string;
  label: string | null;
  created_at: string;
  revoked_at: string | null;
}

export interface ApiTokenCreated extends ApiToken {
  raw_token: string;
}
