"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/useSession";

export default function HomePage() {
  const { session, loading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!loading) router.replace(session ? "/dashboard" : "/login");
  }, [loading, session, router]);

  return <p className="p-8 text-slate-500">Loading…</p>;
}
