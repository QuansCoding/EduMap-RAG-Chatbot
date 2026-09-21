"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import RequireAuth from "@/components/RequireAuth";
import { api, errorMessage } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import type { Workspace } from "@/lib/types";

export default function DashboardPage() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}

function Dashboard() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listWorkspaces()
      .then(setWorkspaces)
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const workspace = await api.createWorkspace(name);
      router.push(`/workspaces/${workspace.id}`);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleJoin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const workspace = await api.joinWorkspace(code);
      router.push(`/workspaces/${workspace.id}`);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  return (
    <main className="mx-auto max-w-4xl p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Your study groups</h1>
        <button onClick={handleSignOut} className="text-sm text-slate-600 hover:underline">
          Sign out
        </button>
      </header>

      {error && <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <form onSubmit={handleCreate} className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold">Create a group</h2>
          <input
            required
            maxLength={100}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. CS 101: Operating Systems"
            className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2"
          />
          <button className="mt-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
            Create
          </button>
        </form>

        <form onSubmit={handleJoin} className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold">Join with an invite code</h2>
          <input
            required
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="e.g. K7MX2QPA"
            className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono tracking-widest"
          />
          <button className="mt-3 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50">
            Join
          </button>
        </form>
      </div>

      <section className="mt-8">
        {loading ? (
          <p className="text-slate-500">Loading…</p>
        ) : workspaces.length === 0 ? (
          <p className="text-slate-500">No groups yet. Create one or join with a code.</p>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {workspaces.map((ws) => (
              <li key={ws.id}>
                <Link
                  href={`/workspaces/${ws.id}`}
                  className="block rounded-xl border border-slate-200 bg-white p-4 hover:border-indigo-400"
                >
                  <p className="font-semibold">{ws.name}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {ws.role === "owner" ? "Owner" : "Member"} · {ws.member_count} member
                    {ws.member_count === 1 ? "" : "s"}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}