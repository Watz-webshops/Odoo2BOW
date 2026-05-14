import { AdminOdooConnectionPageClient } from "./client";

export async function generateStaticParams() {
  return [];
}

export default function AdminOdooConnectionPage() {
  return <AdminOdooConnectionPageClient />;
}
