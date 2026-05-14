import { AdminParticipationsPageClient } from "./client";

export async function generateStaticParams() {
  return [];
}

export default function AdminParticipationsPage() {
  return <AdminParticipationsPageClient />;
}
