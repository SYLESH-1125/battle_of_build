'use client';

import Link from 'next/link';
import { AlertTriangle } from 'lucide-react';

export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-red-100">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
        
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Access Denied
        </h1>
        
        <p className="text-gray-600 mb-6">
          You don&apos;t have permission to access this resource. Your role may not have the required privileges.
        </p>

        <div className="space-y-3">
          <Link
            href="/login"
            className="block w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg transition"
          >
            Return to Login
          </Link>
          
          <Link
            href="/"
            className="block w-full bg-gray-200 hover:bg-gray-300 text-gray-900 font-semibold py-2 px-4 rounded-lg transition"
          >
            Back to Home
          </Link>
        </div>

        <p className="text-gray-500 text-sm mt-6">
          If you believe this is an error, contact your administrator.
        </p>
      </div>
    </div>
  );
}
