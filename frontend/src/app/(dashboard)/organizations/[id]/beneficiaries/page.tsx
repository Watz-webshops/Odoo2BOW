import { AdminBeneficiariesPageClient } from "./client";

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default function AdminBeneficiariesPage() {
  return <AdminBeneficiariesPageClient />;
}
