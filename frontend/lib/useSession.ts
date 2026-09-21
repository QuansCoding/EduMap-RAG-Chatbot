import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";

export function useSession() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    // 1. Read the session saved in the browser (if the user signed in before).
    supabase.auth.getSession().then(({ data }) => {
      if (active) {
        setSession(data.session);
        setLoading(false);
      }
    });

    // 2. Subscribe to future changes (sign in, sign out, token refresh).
    const { data } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    // 3. Cleanup: runs when the component unmounts, which prevents memory leaks.
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []); // [] = run once, when the component first appears

  return { session, loading };
}