"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getRole, isLoggedIn } from "@/lib/auth";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    router.replace(getRole() === "admin" ? "/dashboard" : "/me/dashboard");
  }, [router]);
  return null;
}
