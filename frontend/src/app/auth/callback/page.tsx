'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase-client';
import { Loader2 } from 'lucide-react';

export default function AuthCallbackPage() {
  const router = useRouter();
  const supabase = createClient();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get the session from the URL fragment (Supabase sets this after email link click)
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();

        if (sessionError) {
          throw new Error(sessionError.message);
        }

        if (!session) {
          // If no session, the user needs to verify OTP manually on login page
          router.push('/');
          return;
        }

        // Session is established, fetch user role
        const { data: roleData, error: roleError } = await supabase
          .from('user_roles')
          .select('role')
          .eq('user_id', session.user.id)
          .maybeSingle();

        if (roleError) {
          throw new Error('Unable to fetch user role');
        }

        // Redirect by role (default to patient)
        const userRole = (roleData as { role?: string } | null)?.role ?? 'patient';
        switch (userRole) {
          case 'admin':
            router.push('/admin');
            break;
          case 'doctor':
            router.push('/dashboard');
            break;
          case 'patient':
          default:
            router.push('/patient');
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message || 'Authentication failed. Please try again.');
        // Redirect back to login after 3 seconds
        setTimeout(() => {
          router.push('/');
        }, 3000);
      }
    };

    handleCallback();
  }, [router, supabase]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center bg-white p-8 rounded-lg shadow-lg max-w-sm">
          <h2 className="text-xl font-bold text-red-600 mb-2">Authentication Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <p className="text-sm text-gray-500">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center">
        <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
        <p className="text-gray-700 font-semibold">Completing authentication...</p>
        <p className="text-sm text-gray-600 mt-2">You will be redirected shortly</p>
      </div>
    </div>
  );
}
