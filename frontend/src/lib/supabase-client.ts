"use client";

import { createClient as createSupabaseClient } from '@supabase/supabase-js';
import type { User } from '@supabase/supabase-js';
import { useEffect, useState } from 'react';

// Keep a single Supabase client instance across HMR by attaching it to globalThis
declare global {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  var __supabase_client__: any;
}

export function createClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

  // On the server, create a fresh client (no long-lived browser storage)
  if (typeof window === 'undefined') {
    return createSupabaseClient(url, key);
  }

  // In the browser, reuse a global instance so HMR / Fast Refresh doesn't create duplicates
  const g = globalThis as unknown as { __supabase_client__?: ReturnType<typeof createSupabaseClient> };
  if (!g.__supabase_client__) {
    g.__supabase_client__ = createSupabaseClient(url, key);
  }

  return g.__supabase_client__;
}

export function useSupabase() {
  return createClient();
}

export function useSupabaseAuth() {
  const supabase = createClient();
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user ?? null);

      if (user) {
        // Fetch user role (use maybeSingle to avoid exceptions if none)
        const { data: roleData } = await supabase
          .from('user_roles')
          .select('role')
          .eq('user_id', user.id)
          .maybeSingle();

        setRole((roleData as { role?: string } | null)?.role ?? null);
      }

      setLoading(false);
    };

    fetchUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        if (session?.user) {
          setUser(session.user);

          // Fetch role when auth state changes
          const { data: roleData } = await supabase
            .from('user_roles')
            .select('role')
            .eq('user_id', session.user.id)
            .maybeSingle();

          setRole((roleData as { role?: string } | null)?.role ?? null);
        } else {
          setUser(null);
          setRole(null);
        }
      }
    );

    return () => {
      subscription?.unsubscribe();
    };
  }, [supabase]);

  return { user, role, loading, supabase };
}
