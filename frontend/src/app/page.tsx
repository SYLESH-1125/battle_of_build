'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase-client';
import { Mail, Lock, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import demoConfig from '@/demouser.json';

type AuthStep = 'email-role' | 'otp-input' | 'loading';

interface FormState {
  email: string;
  role: 'doctor' | 'admin' | 'patient';
  otp: string;
  error: string | null;
  showOtpInput: boolean;
  isDemoMode?: boolean;
}

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();
  
  const [step, setStep] = useState<AuthStep>('email-role');
  const [form, setForm] = useState<FormState>({
    email: '',
    role: 'patient',
    otp: '',
    error: null,
    showOtpInput: false,
    isDemoMode: false,
  });
  const [loading, setLoading] = useState(false);
  const [sessionEmail, setSessionEmail] = useState<string>('');

  const redirectByRole = (role: string) => {
    switch (role) {
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
  };

  // Check if user is already logged in
  useEffect(() => {
    const checkSession = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        // User is logged in, fetch their role
        const { data: roleData } = await supabase
          .from('user_roles')
          .select('role')
          .eq('user_id', user.id)
          .maybeSingle();

        const role = (roleData as { role?: string } | null)?.role ?? 'patient';
        redirectByRole(role);
      }
    };

    checkSession();
  }, [router, supabase]);

  const handleSendOtp = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    
    if (!form.email.trim()) {
      setForm(prev => ({ ...prev, error: 'Email is required' }));
      return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(form.email)) {
      setForm(prev => ({ ...prev, error: 'Please enter a valid email address' }));
      return;
    }

    // ✨ DEMO MODE: Check if this is a demo user
    const isDemoUser = demoConfig.demo_users.includes(form.email);
    
    if (isDemoUser) {
      console.log('🎭 Demo mode engaged for:', form.email);
      // Instantly show OTP input without calling Supabase
      setSessionEmail(form.email);
      setForm(prev => ({
        ...prev,
        showOtpInput: true,
        isDemoMode: true,
        error: null,
      }));
      return;
    }

    setLoading(true);
    setForm(prev => ({ ...prev, error: null, isDemoMode: false }));

    try {
      // Send real OTP via Supabase
      const { error } = await supabase.auth.signInWithOtp({
        email: form.email,
        options: {
          emailRedirectTo: `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/auth/callback`,
        },
      });

      if (error) {
        throw new Error(error.message);
      }

      // OTP sent successfully
      setSessionEmail(form.email);
      setForm(prev => ({
        ...prev,
        showOtpInput: true,
        isDemoMode: false,
        error: null,
      }));

    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setForm(prev => ({
        ...prev,
        error: message || 'Failed to send OTP. Please try again.',
      }));
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.SyntheticEvent) => {
    e.preventDefault();

    if (!form.otp || form.otp.length !== 6) {
      setForm(prev => ({ ...prev, error: 'Please enter a valid 6-digit PIN' }));
      return;
    }

    setLoading(true);
    setForm(prev => ({ ...prev, error: null }));

    try {
      let authData: unknown = null;
      
      // ✨ DEMO MODE: If demo user enters 123456, use password auth
      if (form.isDemoMode && form.otp === demoConfig.demo_pin) {
        console.log('🎭 Demo mode: using password authentication');
        const demoPassword = demoConfig.hidden_password_prefix + demoConfig.demo_pin;
        
        const { data, error } = await supabase.auth.signInWithPassword({
          email: sessionEmail,
          password: demoPassword,
        });

        if (error) {
          throw new Error(error.message || 'Invalid PIN. Please try again.');
        }

        authData = data;
      } else if (form.isDemoMode) {
        // Demo user but wrong PIN
        throw new Error('Invalid PIN. For demo mode, use: ' + demoConfig.demo_pin);
      } else {
        // Real OTP verification
        const { data, error } = await supabase.auth.verifyOtp({
          email: sessionEmail,
          token: form.otp,
          type: 'email',
        });

        if (error) {
          throw new Error(error.message);
        }

        authData = data;
      }

        const user = (authData as { user?: { id: string } } | null)?.user;
        if (user) {
        setStep('loading');

        // Fetch user role
        const { data: roleData, error: roleError } = await supabase
          .from('user_roles')
          .select('role')
          .eq('user_id', user.id)
          .maybeSingle();

        if (roleError) {
          throw new Error('Unable to fetch user role. Please contact support.');
        }

        // Redirect by role
        const userRole = (roleData as { role?: string } | null)?.role ?? 'patient';
        redirectByRole(userRole);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setForm(prev => ({
        ...prev,
        error: message || 'Invalid PIN. Please try again.',
        otp: '',
      }));
    } finally {
      setLoading(false);
    }
  };

  const handleBackToEmail = () => {
    setForm(prev => ({
      ...prev,
      showOtpInput: false,
      otp: '',
      error: null,
    }));
    setSessionEmail('');
  };

  // Loading screen
  if (step === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-700 font-semibold">Completing authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-600 text-white rounded-lg mb-4">
            <Lock className="w-6 h-6" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Memory Vault</h1>
          <p className="text-gray-600 mt-2">Secure Medical Data Access</p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-lg shadow-xl p-8">
          {!form.showOtpInput ? (
            // STEP 1: Email & Role Selection
            <form onSubmit={handleSendOtp} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                  <input
                    id="email"
                    type="email"
                    value={form.email}
                    onChange={(e) =>
                      setForm(prev => ({ ...prev, email: e.target.value, error: null }))
                    }
                    placeholder="you@hospital.com"
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    disabled={loading}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Your registered hospital email address
                </p>
              </div>

              <div>
                <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-2">
                  User Role
                </label>
                <select
                  id="role"
                  value={form.role}
                  onChange={(e) =>
                    setForm(prev => ({ ...prev, role: e.target.value as FormState['role'] }))
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  disabled={loading}
                >
                  <option value="patient">Patient</option>
                  <option value="doctor">Doctor / Clinician</option>
                  <option value="admin">Administrator</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Your role in the system (must be pre-provisioned)
                </p>
              </div>

              {/* Error Message */}
              {form.error && (
                <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{form.error}</p>
                </div>
              )}

              {/* Send OTP Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Sending OTP...
                  </>
                ) : (
                  <>
                    <Mail className="w-4 h-4" />
                    Send Secure OTP
                  </>
                )}
              </button>

              <p className="text-xs text-gray-500 text-center">
                A 6-digit PIN will be sent to your email
              </p>
            </form>
          ) : (
            // STEP 2: OTP Verification
            <form onSubmit={handleVerifyOtp} className="space-y-6">
              <div className={`flex items-center justify-center p-4 rounded-lg ${form.isDemoMode ? 'bg-purple-50' : 'bg-blue-50'}`}>
                <CheckCircle2 className={`w-5 h-5 ${form.isDemoMode ? 'text-purple-600' : 'text-blue-600'} mr-2`} />
                <p className={`text-sm ${form.isDemoMode ? 'text-purple-700' : 'text-blue-700'}`}>
                  {form.isDemoMode ? '🎭 Demo Mode' : 'PIN sent to'} <strong>{sessionEmail}</strong>
                </p>
              </div>

              <div>
                <label htmlFor="otp" className="block text-sm font-medium text-gray-700 mb-2">
                  Enter 6-Digit PIN
                </label>
                <input
                  id="otp"
                  type="text"
                  value={form.otp}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                    setForm(prev => ({ ...prev, otp: value, error: null }));
                  }}
                  placeholder="000000"
                  maxLength={6}
                  className="w-full px-4 py-3 text-center text-2xl font-mono border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                  disabled={loading}
                  autoComplete="one-time-code"
                />
                <p className="text-xs text-gray-500 mt-1 text-center">
                  Check your email for the PIN
                </p>
              </div>

              {/* Error Message */}
              {form.error && (
                <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{form.error}</p>
                </div>
              )}

              {/* Verify Button */}
              <button
                type="submit"
                disabled={loading || form.otp.length !== 6}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Verify PIN
                  </>
                )}
              </button>

              {/* Back Button */}
              <button
                type="button"
                onClick={handleBackToEmail}
                disabled={loading}
                className="w-full bg-gray-100 hover:bg-gray-200 disabled:bg-gray-100 text-gray-700 font-semibold py-2 px-4 rounded-lg transition"
              >
                Back to Email
              </button>

              <p className="text-xs text-gray-500 text-center">
                Didn&apos;t receive the PIN? Check spam folder or request a new one
              </p>
            </form>
          )}
        </div>

        {/* Footer Info */}
        <div className="mt-6 text-center text-xs text-gray-600">
          <p>
            🔒 This system uses production-grade Supabase Authentication
          </p>
          <p className="mt-2">
            For pre-provisioned users only. Contact your administrator.
          </p>
        </div>
      </div>
    </div>
  );
}
