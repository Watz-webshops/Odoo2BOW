"use client";

import { ExportPreviewView } from "@/components/ExportPreviewView";
import { useRouteSegment } from "@/lib/route";

export function AdminExportPreviewPageClient() {
  const id = useRouteSegment("/organizations");
  return (
    <ExportPreviewView
      previewPath={`/organizations/${id}/exports/preview`}
      generatePath={`/organizations/${id}/exports/from-local`}
      title="XML voorvertoning"
    />
  );
}
