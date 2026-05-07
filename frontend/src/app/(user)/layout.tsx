"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { getRole, isLoggedIn } from "@/lib/auth";

export default function UserLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    if (getRole() !== "user") {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar role="user" />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
