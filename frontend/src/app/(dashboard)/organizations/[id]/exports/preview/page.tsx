"use client";

import { useParams } from "next/navigation";
import { ExportPreviewView } from "@/components/ExportPreviewView";

export default function AdminExportPreviewPage() {
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
