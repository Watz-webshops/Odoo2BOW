"use client";

import { useParams } from "next/navigation";
import { ExportPreviewView } from "@/components/ExportPreviewView";

export function AdminExportPreviewPageClient() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  return (
    <ExportPreviewView
      previewPath={`/organizations/${id}/exports/preview`}
      generatePath={`/organizations/${id}/exports/from-local`}
      title="XML voorvertoning"
    />
  );
}
