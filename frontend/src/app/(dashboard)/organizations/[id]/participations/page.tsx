import { Suspense } from "react";
import { AdminParticipationsPageClient } from "./client";

export async function generateStaticParams() {
  return [{ id: "_" }];
}

export default function AdminParticipationsPage() {
  return (
    <Suspense>
      <AdminParticipationsPageClient />
    </Suspense>
  );
}
