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
}

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
