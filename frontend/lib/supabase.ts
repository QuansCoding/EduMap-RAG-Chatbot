import { createClient } from "@supabase/supabase-js";

// One shared client for the whole app. We only use it for AUTH;
// all data goes through our FastAPI backend.
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
);