import { AdminBeneficiariesPageClient } from "./client";

export async function generateStaticParams() {
  return [];
}

export default function AdminBeneficiariesPage() {
  return <AdminBeneficiariesPageClient />;
}
