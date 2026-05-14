import { MyExportDetailPageClient } from "./client";

export async function generateStaticParams() {
  return [];
}

export default function MyExportDetailPage() {
  return <MyExportDetailPageClient />;
}
