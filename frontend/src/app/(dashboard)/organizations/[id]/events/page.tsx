import { AdminEventsPageClient } from "./client";

export async function generateStaticParams() {
  return [];
}

export default function AdminEventsPage() {
  return <AdminEventsPageClient />;
}
