"use client";

import { ExportPreviewView } from "@/components/ExportPreviewView";

export default function MeExportPreviewPage() {
  return (
    <ExportPreviewView
      previewPath="/me/exports/preview"
      generatePath="/me/exports/from-local"
      title="XML voorvertoning"
    />
  );
}
