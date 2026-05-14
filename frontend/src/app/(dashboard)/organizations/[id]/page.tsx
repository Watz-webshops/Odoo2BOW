import { OrgDetailPageClient } from "./client";

export async function generateStaticParams() {
  return [];
}

export default function OrgDetailPage() {
  return <OrgDetailPageClient />;
}
