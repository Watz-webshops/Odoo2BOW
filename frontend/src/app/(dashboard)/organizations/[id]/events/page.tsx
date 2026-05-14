import { AdminEventsPageClient } from "./client";

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default function AdminEventsPage() {
  return <AdminEventsPageClient />;
}
