import { AdminExportPreviewPageClient } from "./client";

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default function AdminExportPreviewPage() {
  return <AdminExportPreviewPageClient />;
}
