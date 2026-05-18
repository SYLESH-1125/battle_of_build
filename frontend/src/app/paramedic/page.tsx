"use client";

export const dynamic = 'force-dynamic';

import React, { useMemo, useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Ambulance, ShieldCheck, FileText, UploadCloud, AlertTriangle } from "lucide-react";
import StatusBanner, { StatusVariant } from "@/components/StatusBanner";
import { ingestRecord, IngestPayload } from "@/lib/api";

type StatusState = StatusVariant | "idle";

export default function ParamedicDashboard() {
  const [patientId, setPatientId] = useState("");
  const [rawText, setRawText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<StatusState>("idle");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [paramedicId, setParamedicId] = useState<string>('');

  useEffect(() => {
    setParamedicId(localStorage.getItem('mock_user_id') ?? '');
  }, []);

  const isSubmitting = status === "submitting";

  const statusContent = useMemo(() => {
    if (status === "idle") return null;
    const defaults: Record<StatusVariant, { title: string; description: string }> = {
      submitting: { title: "Transmitting emergency record", description: "Sending to vault..." },
      success: { title: "Emergency record accepted", description: "Record queued for immediate processing." },
      blocked: { title: "Blocked by privacy filter", description: "Content matched the ignore list." },
      error: { title: "Transmission failed", description: "Check connectivity and retry." },
    };
    return { title: defaults[status as StatusVariant].title, description: statusMessage ?? defaults[status as StatusVariant].description };
  }, [status, statusMessage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("submitting");
    setStatusMessage(null);

    const payload: IngestPayload = {
      patient_id: patientId.trim(),
      raw_text: rawText.trim(),
      doctor_id: paramedicId || undefined,
      file_url: selectedFile?.name,
    };

    const result = await ingestRecord(payload);
    const msg =
      result.data && typeof result.data === "object"
        ? (String((result.data as Record<string, unknown>).message ?? (result.data as Record<string, unknown>).detail ?? ""))
        : null;
    if (msg) setStatusMessage(msg);

    if (result.status === 403) { setStatus("blocked"); return; }
    setStatus(result.ok ? "success" : "error");
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10 sm:px-8">
      <div className="mx-auto w-full max-w-4xl space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="rounded-3xl bg-white p-8 shadow-[0_30px_60px_-40px_rgba(15,23,42,0.35)]"
        >
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-orange-500 text-white">
                  <Ambulance size={22} />
                </span>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Emergency Intake</p>
                  <h1 className="text-2xl font-extrabold text-slate-900">Paramedic Field Dashboard</h1>
                </div>
              </div>
              <p className="max-w-xl text-sm text-slate-600">
                Submit emergency field notes directly to the vault. Records are triaged and processed immediately.
              </p>
            </div>
            <div className="rounded-2xl border border-orange-100 bg-orange-50 px-4 py-3">
              <div className="flex items-center gap-2 text-sm">
                <Ambulance size={16} className="text-orange-500" />
                <span className="font-semibold text-slate-700">{paramedicId || "PARA-XXXXX"}</span>
              </div>
            </div>
          </div>

          {/* Priority warning banner */}
          <div className="mt-6 flex items-start gap-3 rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm text-orange-700">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
            <p>
              <span className="font-bold">Field Mode:</span> Records submitted here are flagged as emergency intake and prioritised for immediate AI processing and admin review.
            </p>
          </div>

          {status !== "idle" && statusContent && (
            <div className="mt-4">
              <StatusBanner variant={status as StatusVariant} title={statusContent.title} description={statusContent.description} />
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Patient ID / ABHA</label>
                <input
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  placeholder="ABHA-2024-XXXXX"
                  required
                  className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-900 shadow-sm focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-200"
                />
              </div>
              <div>
                <label className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Optional File / Scan</label>
                <div className="mt-2 flex items-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  <UploadCloud size={18} className="text-slate-400 shrink-0" />
                  <span className="flex-1 truncate font-semibold text-slate-700">
                    {selectedFile ? selectedFile.name : "No file selected"}
                  </span>
                  <label className="cursor-pointer rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm hover:border-slate-300">
                    Browse
                    <input type="file" className="hidden" onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)} />
                  </label>
                </div>
              </div>
            </div>

            <div>
              <label className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Field Triage Notes</label>
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="GCS, vitals, mechanism of injury, interventions applied, allergies observed..."
                required
                rows={8}
                className="mt-2 w-full resize-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-900 shadow-sm focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-200"
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <FileText size={13} />
                Posting to <span className="font-semibold">/ingest</span> on localhost:8000
              </div>
              <motion.button
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center gap-2 rounded-2xl bg-orange-500 px-6 py-3 text-sm font-semibold text-white shadow-[0_10px_20px_-10px_rgba(249,115,22,0.5)] transition hover:bg-orange-600 disabled:opacity-70"
              >
                <ShieldCheck size={18} />
                {isSubmitting ? "Transmitting..." : "Submit Emergency Record"}
              </motion.button>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
