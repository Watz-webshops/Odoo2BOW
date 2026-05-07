"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Building2,
  FileText,
  KeyRound,
  LayoutDashboard,
  LogOut,
  ScrollText,
  ShieldUser,
  User as UserIcon,
  Users,
} from "lucide-react";
import { clearSession } from "@/lib/auth";
import { cn } from "@/lib/utils";

type Role = "admin" | "user";

const ADMIN_NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/organizations", label: "Organisaties", icon: Building2 },
  { href: "/users", label: "Users", icon: Users },
  { href: "/admins", label: "Admins", icon: ShieldUser },
  { href: "/exports", label: "Exports", icon: FileText },
  { href: "/audit-log", label: "Audit log", icon: ScrollText },
  { href: "/profile", label: "Profiel", icon: UserIcon },
];

const USER_NAV = [
  { href: "/me/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/me/exports", label: "Exports", icon: FileText },
  { href: "/me/beneficiaries", label: "Begunstigden", icon: Users },
  { href: "/me/participations", label: "Deelnames", icon: ScrollText },
  { href: "/me/api-tokens", label: "API Tokens", icon: KeyRound },
  { href: "/me/profile", label: "Profiel", icon: UserIcon },
];

export function Sidebar({ role }: { role: Role }) {
  const pathname = usePathname();
  const router = useRouter();
  const nav = role === "admin" ? ADMIN_NAV : USER_NAV;

  function logout() {
    clearSession();
    router.push("/login");
  }

  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
      <div className="px-4 py-5 border-b border-gray-200">
        <span className="font-semibold text-gray-900 text-sm">Odoo2BOW</span>
        <p className="text-xs text-gray-500 mt-0.5">
          {role === "admin" ? "Admin paneel" : "Gebruiker"}
        </p>
      </div>

      <nav className="flex-1 py-4 space-y-1 px-2">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              pathname === href || pathname.startsWith(href + "/")
                ? "bg-brand-50 text-brand-700"
                : "text-gray-600 hover:bg-gray-100"
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </Link>
        ))}
      </nav>

      <div className="px-2 pb-4">
        <button
          onClick={logout}
          className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Uitloggen
        </button>
      </div>
    </aside>
  );
}
