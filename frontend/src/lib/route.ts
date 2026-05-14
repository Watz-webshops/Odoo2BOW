"use client";

import { usePathname } from "next/navigation";

/**
 * Extract a dynamic route segment from the URL pathname.
 *
 * Workaround for Next.js static export: `useParams()` returns the build-time
 * placeholder (`_`) instead of the real value, because `generateStaticParams`
 * only emits `[{ id: "_" }]`. Reading from the URL gives us the actual id.
 */
export function useRouteSegment(prefix: string): string {
  const pathname = usePathname() ?? "";
  if (!pathname.startsWith(prefix + "/")) return "";
  const rest = pathname.slice(prefix.length + 1);
  const slash = rest.indexOf("/");
  return slash === -1 ? rest : rest.slice(0, slash);
}
