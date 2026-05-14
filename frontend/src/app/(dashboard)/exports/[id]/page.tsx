import { ExportDetailPageClient } from "./client";

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default function ExportDetailPage() {
  return <ExportDetailPageClient />;
}
