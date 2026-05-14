import { MyExportDetailPageClient } from "./client";

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default function MyExportDetailPage() {
  return <MyExportDetailPageClient />;
}
