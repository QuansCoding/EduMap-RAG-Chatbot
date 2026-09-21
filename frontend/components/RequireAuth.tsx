"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/useSession";

/** Renders children only for signed-in users; otherwise redirects to /login. */
export default function RequireAuth({ children }: { children: ReactNode }) {
  const { session, loading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !session) router.replace("/login");
  }, [loading, session, router]);

  if (loading || !session) {
    return <div className="p-8 text-slate-500">Loading…</div>;
  }
  return <>{children}</>;
}