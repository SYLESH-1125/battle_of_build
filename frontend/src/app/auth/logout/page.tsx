'use client';

export const dynamic = 'force-dynamic';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase-client';
import { Loader2 } from 'lucide-react';

export default function LogoutPage() {
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    const handleLogout = async () => {
      try {
        // Sign out the user
        const { error } = await supabase.auth.signOut();

        if (error) {
          throw new Error(error.message);
        }

        // Clear any local state if needed
        // Redirect to login page
        router.push('/');
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        console.error('Logout error:', message);
        // Still redirect to login even if logout fails
        setTimeout(() => {
          router.push('/');
        }, 1000);
      }
    };

    handleLogout();
  }, [router, supabase]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center">
        <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
        <p className="text-gray-700 font-semibold">Signing you out...</p>
        <p className="text-sm text-gray-600 mt-2">You will be redirected shortly</p>
      </div>
    </div>
  );
}
