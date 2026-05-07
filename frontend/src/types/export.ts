export type ExportStatus = "pending" | "processing" | "completed" | "failed";

export interface ExportSummaryWarning {
  type: string;
  parent_rrn: string;
  child_rrn: string;
  message: string;
}

export interface ExportSummary {
  fiche_count: number;
  total_amount_cents: number;
  total_days: number;
  skipped_count: number;
  warnings: ExportSummaryWarning[];
  errors: string[];
}

export interface ExportRecord {
  export_id: string;
  status: ExportStatus;
  summary: ExportSummary | null;
  error_detail: string | null;
}

export interface ExportCreated {
  export_id: string;
  status: string;
}
