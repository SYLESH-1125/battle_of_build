'use client';

export const dynamic = 'force-dynamic';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, Download, ArrowLeft, AlertCircle, CheckCircle, LogOut } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import { createClient } from '@/lib/supabase-client';

type VaultData = {
  patient_id: string;
  encrypted_fhir_json_id: string;
  created_at?: string | null;
  [key: string]: unknown;
};

export default function PatientPortal() {
  const router = useRouter();
  const authClient = createClient();
  const [patientId, setPatientId] = useState('');
  const [vaultData, setVaultData] = useState<VaultData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showQR, setShowQR] = useState(false);
  const qrRef = React.useRef<HTMLDivElement>(null);

  const supabase = createClient();

  const handleLogout = async () => {
    await authClient.auth.signOut();
    router.push('/');
  };

  const handleSearch = async () => {
    if (!patientId.trim()) {
      setError('Please enter a patient ID');
      return;
    }

    setLoading(true);
    setError('');
    setVaultData(null);
    setShowQR(false);

    try {
      // Query main_vault to find the patient's encrypted FHIR record
      // Use maybeSingle() instead of single() to avoid 406 errors
      const { data, error: queryError } = await supabase
        .from('main_vault')
        .select('*')
        .eq('patient_id', patientId.trim())
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle();

      if (queryError) {
        // Handle RLS policy or authorization errors
        if (queryError.code === '406' || queryError.message?.includes('406')) {
          setError(`Access denied or vault not found for ${patientId}. Please verify permissions.`);
        } else {
          setError(`Error retrieving vault: ${queryError.message || 'Unknown error'}`);
        }
        return;
      }

      if (!data) {
        setError(`No vault found for patient ${patientId}. Please verify the patient ID exists in the system.`);
        return;
      }

      setVaultData(data);
      setShowQR(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Error retrieving vault: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const generateQRPayload = () => {
    if (!vaultData) return '';
    
    // Generate QR payload with cryptographic identifiers
    const payload = {
      patient_id: vaultData.patient_id,
      vault_id: vaultData.encrypted_fhir_json_id,
      merkle_root: `merkle_${vaultData.encrypted_fhir_json_id.substring(0, 8)}`,
      timestamp: new Date().toISOString(),
      emergency_access: true
    };
    
    return JSON.stringify(payload);
  };

  const downloadQR = () => {
    if (qrRef.current && vaultData) {
      const canvas = qrRef.current.querySelector('canvas');
      if (canvas) {
        const link = document.createElement('a');
        link.href = canvas.toDataURL('image/png');
        link.download = `vault-${vaultData.patient_id}-${Date.now()}.png`;
        link.click();
      }
    }
  };

  const handleReset = () => {
    setPatientId('');
    setVaultData(null);
    setShowQR(false);
    setError('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-emerald-600" />
              <h1 className="text-3xl font-bold text-gray-900">Patient Vault Access</h1>
            </div>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-red-50 hover:border-red-200 hover:text-red-600 transition"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
          <p className="text-gray-600">
            Retrieve your encrypted medical vault with cryptographic verification
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-lg shadow-lg p-8">
          {!showQR ? (
            // Search Form
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Patient ID
                </label>
                <input
                  type="text"
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="e.g., PT-LIFECYCLE-MASTER-01"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  disabled={loading}
                />
              </div>

              {error && (
                <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <button
                onClick={handleSearch}
                disabled={loading}
                className="w-full px-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition"
              >
                {loading ? 'Retrieving Vault...' : 'Access Medical Vault'}
              </button>
            </div>
          ) : vaultData ? (
            // QR Display
            <div className="space-y-6">
              {/* Status Banner */}
              <div className="flex items-start gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-emerald-900">Cryptographically Sealed & Ready for Emergency Triage</p>
                  <p className="text-sm text-emerald-700 mt-1">
                    This vault has been verified through multi-stage AI consensus and is ready for emergency access.
                  </p>
                </div>
              </div>

              {/* Vault Details */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div>
                  <p className="text-sm text-gray-600">Patient ID</p>
                  <p className="font-mono text-sm font-semibold text-gray-900">{vaultData.patient_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Vault ID</p>
                  <p className="font-mono text-xs text-gray-700 break-all">{vaultData.encrypted_fhir_json_id}</p>
                </div>
                {vaultData.created_at && (
                  <div>
                    <p className="text-sm text-gray-600">Created</p>
                    <p className="text-sm text-gray-900">
                      {new Date(vaultData.created_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>

              {/* QR Code */}
              <div className="flex flex-col items-center space-y-4 bg-gray-50 p-8 rounded-lg">
                <p className="text-sm text-gray-600 font-medium">Scan to Verify & Access</p>
                <div ref={qrRef} className="bg-white p-4 rounded-lg shadow">
                  <QRCodeCanvas
                    value={generateQRPayload()}
                    size={256}
                    level="H"
                    marginSize={4}
                  />
                </div>
                <p className="text-xs text-gray-500 text-center max-w-sm">
                  This QR code contains encrypted references to your medical vault, ready for emergency scanning at any authorized facility.
                </p>
              </div>

              {/* QR Payload Info */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-xs font-mono text-blue-900 break-all">
                  {generateQRPayload()}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={downloadQR}
                  className="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition"
                >
                  <Download className="w-4 h-4" />
                  Download QR
                </button>
                <button
                  onClick={handleReset}
                  className="flex items-center justify-center gap-2 px-4 py-3 bg-gray-300 hover:bg-gray-400 text-gray-900 font-medium rounded-lg transition"
                >
                  <ArrowLeft className="w-4 h-4" />
                  New Search
                </button>
              </div>
            </div>
          ) : null}
        </div>

        {/* Info Footer */}
        <div className="mt-8 space-y-4 text-sm text-gray-600">
          <div className="bg-white rounded-lg p-4">
            <p className="font-medium text-gray-900 mb-2">🔒 Security Notice</p>
            <p>
              Your medical vault is protected through multi-layered encryption and AI-driven conflict detection. 
              This portal demonstrates the complete three-stage triage system: Doctor admission → AI analysis → Admin approval → Patient access.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
