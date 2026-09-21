"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, errorMessage } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { useSession } from "@/lib/useSession";

const DEMO_EMAIL = process.env.NEXT_PUBLIC_DEMO_EMAIL;
const DEMO_PASSWORD = process.env.NEXT_PUBLIC_DEMO_PASSWORD;

export default function LoginPage() {
  const router = useRouter();
  const { session } = useSession();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [serverAwake, setServerAwake] = useState<boolean | null>(null);

  // Already signed in? Skip the login page.
  useEffect(() => {
    if (session) router.replace("/dashboard");
  }, [session, router]);

  // Free hosting sleeps when idle. Ping the backend now so it's awake by the time the user signs in.
  useEffect(() => {
    api.health().then(setServerAwake);
  }, []);

  async function signIn(emailValue: string, passwordValue: string) {
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: emailValue,
      password: passwordValue,
    });
    if (signInError) throw signInError;
    router.replace("/dashboard");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (mode === "signup") {
        const { data, error: signUpError } = await supabase.auth.signUp({ email, password });
        if (signUpError) throw signUpError;
        if (!data.session) {
          setNotice("Check your email to confirm your account, then sign in.");
          return;
        }
        router.replace("/dashboard");
      } else {
        await signIn(email, password);
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDemo() {
    if (!DEMO_EMAIL || !DEMO_PASSWORD) return;
    setBusy(true);
    setError(null);
    try {
      await signIn(DEMO_EMAIL, DEMO_PASSWORD);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold">EduMap</h1>
        <p className="mt-1 text-sm text-slate-500">Study smarter with your course materials.</p>

        {serverAwake === null && (
          <p className="mt-4 rounded-md bg-sky-50 px-3 py-2 text-xs text-sky-800">
            Waking up the server… the first load can take up to a minute on free hosting.
          </p>
        )}
        {serverAwake === false && (
          <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-xs text-red-800">
            Can&apos;t reach the server right now. Please try again shortly.
          </p>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <label className="block">
            <span className="text-sm font-medium">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Password</span>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-indigo-500"
            />
          </label>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {notice && <p className="text-sm text-emerald-700">{notice}</p>}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-indigo-600 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
          className="mt-4 w-full text-sm text-indigo-600 hover:underline"
        >
          {mode === "signin" ? "New here? Create an account" : "Already have an account? Sign in"}
        </button>

        {DEMO_EMAIL && DEMO_PASSWORD && (
          <button
            type="button"
            onClick={handleDemo}
            disabled={busy}
            className="mt-3 w-full rounded-lg border border-slate-300 py-2 text-sm hover:bg-slate-50 disabled:opacity-50"
          >
            Try the demo account
          </button>
        )}
      </div>
    </main>
  );
}