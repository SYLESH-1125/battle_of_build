"use client";

export const dynamic = 'force-dynamic';

import React, { useMemo, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  FileText,
  ShieldCheck,
  UploadCloud,
  UserCircle,
  LogOut,
} from "lucide-react";
import StatusBanner, { StatusVariant } from "@/components/StatusBanner";
import { ingestRecord, IngestPayload } from "@/lib/api";
import { createClient } from "@/lib/supabase-client";

type StatusState = StatusVariant | "idle";

type LocalSession = {
  role: string;
  userId: string;
};

const emptySession: LocalSession = {
  role: "",
  userId: "",
};

export default function DashboardPage() {
  const router = useRouter();
  const supabase = createClient();
  const [patientId, setPatientId] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [rawText, setRawText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<StatusState>("idle");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [session, setSession] = useState<LocalSession>(emptySession);

  useEffect(() => {
    // Read localStorage only after mount to keep server and client HTML consistent
    setSession({
      role: localStorage.getItem('mock_role') ?? '',
      userId: localStorage.getItem('mock_user_id') ?? '',
    });
  }, []);

  const isSubmitting = status === "submitting";

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/');
  };

  const statusContent = useMemo(() => {
    if (status === "idle") {
      return null;
    }

    const defaults: Record<StatusVariant, { title: string; description: string }>
      = {
      submitting: {
        title: "Submitting intake",
        description: "Sending payload to /ingest. Waiting for response.",
      },
      success: {
        title: "Accepted",
        description: "Record queued for processing.",
      },
      blocked: {
        title: "Blocked by privacy filter",
        description: "This content matched the ignore list.",
      },
      error: {
        title: "Ingest failed",
        description: "Check the API service and try again.",
      },
    };

    const content = defaults[status];
    const description = statusMessage || content.description;

    return {
      title: content.title,
      description,
    };
  }, [status, statusMessage]);

  const parseMessage = (data: unknown): string | null => {
    if (!data || typeof data !== "object") {
      return null;
    }

    const record = data as Record<string, unknown>;
    const message = record.message ?? record.detail;

    if (typeof message === "string" && message.trim().length > 0) {
      return message;
    }

    return null;
  };

  const handleSubmit = async (event: React.SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus("submitting");
    setStatusMessage(null);

    const payload: IngestPayload = {
      patient_id: patientId.trim(),
      raw_text: rawText.trim(),
    };

    if (doctorId.trim().length > 0) {
      payload.doctor_id = doctorId.trim();
    }

    if (selectedFile) {
      payload.file_url = selectedFile.name;
    }

    const result = await ingestRecord(payload);
    const message = parseMessage(result.data);

    if (message) {
      setStatusMessage(message);
    }

    if (result.status === 403) {
      setStatus("blocked");
      return;
    }

    if (result.ok) {
      setStatus("success");
      return;
    }

    setStatus("error");
  };

  return (
    /* Root: viewport-locked column */
    <div style={{ height: "100vh", overflow: "hidden", display: "flex", flexDirection: "column", background: "#f8fafc" }}>

      {/* ── TOPBAR ─────────────────────────────────────────── */}
      <div style={{ flexShrink: 0, height: 56, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 28px", background: "white", borderBottom: "1px solid #e2e8f0", zIndex: 50 }}>

        {/* Left: logo + divider + page label */}
        <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, background: "#C8392B", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}>
              <ShieldCheck size={14} />
            </div>
            <span style={{ fontSize: 15, fontWeight: 800, color: "#0f172a", letterSpacing: "-0.01em" }}>DHMV</span>
          </div>
          <div style={{ width: 1, height: 20, background: "#e2e8f0", margin: "0 16px" }} />
          <span style={{ fontSize: 13, color: "#94a3b8", fontWeight: 500 }}>Hospital Trigger</span>
        </div>

        {/* Right: doctor badge + logout */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 20, padding: "5px 12px 5px 8px" }}>
            <UserCircle size={16} style={{ color: "#475569" }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: "#0f172a" }}>
              {session.role || "Doctor"}
            </span>
            <span style={{ fontSize: 12, color: "#94a3b8" }}>
              / {session.userId || "DL-MCI-2024-XXXXX"}
            </span>
          </div>
          <button
            onClick={handleLogout}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 14px", borderRadius: 8, border: "1px solid #e2e8f0", background: "transparent", fontSize: 13, fontWeight: 500, color: "#475569", cursor: "pointer" }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "#fef2f2"; e.currentTarget.style.borderColor = "#fca5a5"; e.currentTarget.style.color = "#dc2626"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.color = "#475569"; }}
          >
            <LogOut size={13} />
            Logout
          </button>
        </div>
      </div>

      {/* ── SCROLLABLE CONTENT ─────────────────────────────── */}
      <div style={{ flex: 1, overflowY: "auto", padding: 28, display: "flex", flexDirection: "column", gap: 20 }}>
        {/* max-width wrapper so cards don't stretch on ultrawide */}
        <div style={{ maxWidth: 1200, margin: "0 auto", width: "100%", display: "flex", flexDirection: "column", gap: 20 }}>

        {/* ── FIX 1: HERO HEADER CARD — compact ── */}
        <div style={{ background: "#0f172a", borderRadius: 12, padding: "20px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", overflow: "hidden", flexShrink: 0 }}>

          {/* Left content */}
          <div>
            {/* Live pill — smaller */}
            <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "rgba(200,57,43,0.15)", border: "1px solid rgba(200,57,43,0.3)", borderRadius: 20, padding: "3px 10px", marginBottom: 8 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#C8392B", display: "inline-block", animation: "pulse 1.5s ease-in-out infinite" }} />
              <span style={{ fontSize: 10, fontWeight: 600, color: "#ff7b72", letterSpacing: "0.06em" }}>PHASE 1 INTAKE — ACTIVE</span>
            </div>

            <h1 style={{ fontSize: 22, fontWeight: 800, color: "white", margin: "0 0 6px 0" }}>
              Hospital Trigger Dashboard
            </h1>
            <p style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", maxWidth: 420, lineHeight: 1.6, margin: 0 }}>
              Submit a new clinical note to the vault. Records are screened against the privacy filter before they are queued for processing.
            </p>

            {/* Stat pills — smaller */}
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              {[["AES-256", "Encryption"], ["FHIR R4", "Standard"], ["HIPAA", "Compliant"]].map(([val, lbl]) => (
                <div key={lbl} style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, padding: "6px 12px", display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "white" }}>{val}</span>
                  <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{lbl}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: decorative shield circle — smaller */}
          <div style={{ width: 72, height: 72, borderRadius: "50%", background: "rgba(200,57,43,0.15)", border: "1px solid rgba(200,57,43,0.25)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <ShieldCheck size={36} style={{ color: "#C8392B" }} />
          </div>
        </div>

        {/* ── SECTION 2: FORM CARD ── */}
        <div style={{ background: "white", borderRadius: 14, border: "1px solid #e2e8f0", overflow: "hidden", flexShrink: 0 }}>

          {/* Form card header */}
          <div style={{ padding: "16px 24px", borderBottom: "1px solid #e2e8f0", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <FileText size={16} style={{ color: "#C8392B" }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: "#0f172a" }}>Clinical Record Submission</span>
              <span style={{ fontSize: 12, color: "#94a3b8" }}>— All fields encrypted before transmission</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#16a34a", display: "inline-block", animation: "pulse 1.5s ease-in-out infinite" }} />
              <span style={{ fontSize: 12, color: "#16a34a", fontWeight: 500 }}>Vault Ready</span>
            </div>
          </div>

          {/* Status banner if needed */}
          {status !== "idle" && statusContent && (
            <div style={{ padding: "0 24px 0 24px", marginTop: 16 }}>
              <StatusBanner
                variant={status as StatusVariant}
                title={statusContent.title}
                description={statusContent.description}
              />
            </div>
          )}

          {/* Form body */}
          <form onSubmit={handleSubmit}>
            <div style={{ padding: 24, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px 28px" }}>

              {/* LEFT COLUMN */}
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

                {/* Patient ID */}
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.07em", display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#C8392B", display: "inline-block" }} />
                    Patient ID
                  </label>
                  <input
                    value={patientId}
                    onChange={(event) => setPatientId(event.target.value)}
                    placeholder="ABHA-2024-XXXXX"
                    required
                    style={{ width: "100%", padding: "11px 14px", border: "1.5px solid #e2e8f0", borderRadius: 10, fontSize: 14, color: "#0f172a", background: "#f8fafc", outline: "none", boxSizing: "border-box", transition: "border-color 0.2s, box-shadow 0.2s" }}
                    onFocus={(e) => { e.target.style.borderColor = "#C8392B"; e.target.style.boxShadow = "0 0 0 3px rgba(200,57,43,0.08)"; e.target.style.background = "white"; }}
                    onBlur={(e) => { e.target.style.borderColor = "#e2e8f0"; e.target.style.boxShadow = "none"; e.target.style.background = "#f8fafc"; }}
                  />
                  <span style={{ fontSize: 11, color: "#94a3b8" }}>Accepts ABHA format or internal hospital ID</span>
                </div>

                {/* Clinician ID */}
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.07em", display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#94a3b8", display: "inline-block" }} />
                    Clinician ID
                    <span style={{ fontSize: 10, background: "#f1f5f9", color: "#94a3b8", padding: "1px 6px", borderRadius: 4, fontWeight: 500, textTransform: "none", letterSpacing: "normal" }}>Optional</span>
                  </label>
                  <input
                    value={doctorId}
                    onChange={(event) => setDoctorId(event.target.value)}
                    placeholder="DL-MCI-2024-XXXXX"
                    style={{ width: "100%", padding: "11px 14px", border: "1.5px solid #e2e8f0", borderRadius: 10, fontSize: 14, color: "#0f172a", background: "#f8fafc", outline: "none", boxSizing: "border-box", transition: "border-color 0.2s, box-shadow 0.2s" }}
                    onFocus={(e) => { e.target.style.borderColor = "#C8392B"; e.target.style.boxShadow = "0 0 0 3px rgba(200,57,43,0.08)"; e.target.style.background = "white"; }}
                    onBlur={(e) => { e.target.style.borderColor = "#e2e8f0"; e.target.style.boxShadow = "none"; e.target.style.background = "#f8fafc"; }}
                  />
                </div>

                {/* FIX 3: File attachment with delete button */}
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.07em", display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#94a3b8", display: "inline-block" }} />
                    Attachment
                  </label>

                  {selectedFile ? (
                    /* STATE B: file selected — show row with delete */
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8 }}>
                        <div style={{ width: 32, height: 32, borderRadius: 6, background: "#eff6ff", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                          <FileText size={16} style={{ color: "#2563eb" }} />
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 500, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {selectedFile.name}
                          </div>
                          <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 1 }}>Filename logged only</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => setSelectedFile(null)}
                          title="Remove file"
                          style={{ width: 28, height: 28, borderRadius: 6, background: "#fef2f2", border: "1px solid #fecaca", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0, color: "#dc2626", fontSize: 16, fontWeight: 700, lineHeight: 1 }}
                        >
                          ×
                        </button>
                      </div>
                      {/* Add more files button */}
                      <label
                        style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "7px 12px", background: "transparent", border: "1px dashed #e2e8f0", borderRadius: 8, fontSize: 12, fontWeight: 500, color: "#64748b", cursor: "pointer", width: "100%", marginTop: 6, boxSizing: "border-box", transition: "border-color 0.2s, color 0.2s" }}
                        onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#C8392B"; e.currentTarget.style.color = "#C8392B"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.color = "#64748b"; }}
                      >
                        <UploadCloud size={13} />
                        Add / replace file
                        <input type="file" style={{ display: "none" }} onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
                      </label>
                    </div>
                  ) : (
                    /* STATE A: no file — drop zone */
                    <label
                      style={{ border: "1.5px dashed #e2e8f0", borderRadius: 10, padding: 16, background: "#f8fafc", display: "flex", alignItems: "center", gap: 12, cursor: "pointer", transition: "border-color 0.2s, background 0.2s" }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#C8392B"; e.currentTarget.style.background = "#fef2f2"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.background = "#f8fafc"; }}
                    >
                      <UploadCloud size={24} style={{ color: "#94a3b8", flexShrink: 0 }} />
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 500, color: "#475569", margin: 0 }}>Drop file or click to browse</p>
                        <p style={{ fontSize: 11, color: "#94a3b8", margin: "2px 0 0 0" }}>File content not uploaded — filename logged only</p>
                      </div>
                      <input type="file" style={{ display: "none" }} onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
                    </label>
                  )}
                </div>
              </div>

              {/* RIGHT COLUMN */}
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

                {/* Clinical note */}
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.07em", display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#C8392B", display: "inline-block" }} />
                    Clinical Note
                  </label>
                  <textarea
                    value={rawText}
                    onChange={(event) => setRawText(event.target.value)}
                    placeholder="Paste triage summary, vitals, and urgent history..."
                    required
                    style={{ width: "100%", height: 180, padding: "12px 14px", border: "1.5px solid #e2e8f0", borderRadius: 10, fontSize: 13, color: "#0f172a", background: "#f8fafc", resize: "none", outline: "none", lineHeight: 1.6, fontFamily: "inherit", boxSizing: "border-box", transition: "border-color 0.2s, box-shadow 0.2s" }}
                    onFocus={(e) => { e.target.style.borderColor = "#C8392B"; e.target.style.boxShadow = "0 0 0 3px rgba(200,57,43,0.08)"; e.target.style.background = "white"; }}
                    onBlur={(e) => { e.target.style.borderColor = "#e2e8f0"; e.target.style.boxShadow = "none"; e.target.style.background = "#f8fafc"; }}
                  />
                </div>

                {/* Privacy notice */}
                <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: "14px 16px", display: "flex", gap: 10 }}>
                  <FileText size={18} style={{ color: "#2563eb", flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: "#1d4ed8", margin: "0 0 4px 0" }}>Privacy Filter Active</p>
                    <p style={{ fontSize: 12, color: "#3b82f6", lineHeight: 1.5, margin: 0 }}>
                      Submissions are filtered against vault_ignore.json. Billing or administrative content will be blocked automatically.
                    </p>
                    <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                      {["billing", "psych_notes", "doctor_memos"].map((tag) => (
                        <span key={tag} style={{ fontSize: 10, background: "#dbeafe", color: "#1e40af", padding: "2px 8px", borderRadius: 4, fontWeight: 500 }}>{tag}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Form card footer */}
            <div style={{ padding: "16px 24px", borderTop: "1px solid #f1f5f9", display: "flex", alignItems: "center", justifyContent: "space-between", background: "#fafafa" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <UploadCloud size={14} style={{ color: "#94a3b8" }} />
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>
                    Posting to <strong>/ingest</strong> on localhost:8000
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#16a34a", display: "inline-block", animation: "pulse 1.5s ease-in-out infinite" }} />
                  <span style={{ fontSize: 11, color: "#16a34a" }}>Connected</span>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                style={{ display: "flex", alignItems: "center", gap: 8, background: isSubmitting ? "#9B2D21" : "#C8392B", color: "white", border: "none", borderRadius: 10, padding: "12px 28px", fontSize: 14, fontWeight: 700, cursor: isSubmitting ? "not-allowed" : "pointer", letterSpacing: "0.02em", transition: "background 0.2s, transform 0.1s", opacity: isSubmitting ? 0.8 : 1 }}
                onMouseEnter={(e) => { if (!isSubmitting) e.currentTarget.style.background = "#9B2D21"; }}
                onMouseLeave={(e) => { if (!isSubmitting) e.currentTarget.style.background = "#C8392B"; }}
                onMouseDown={(e) => { if (!isSubmitting) e.currentTarget.style.transform = "scale(0.98)"; }}
                onMouseUp={(e) => { e.currentTarget.style.transform = "scale(1)"; }}
              >
                <ShieldCheck size={16} />
                {isSubmitting ? "Submitting…" : "Submit to Vault"}
              </button>
            </div>
          </form>
        </div>

        {/* ── FIX 2: PIPELINE — real arrows ── */}
        <div style={{ flexShrink: 0, background: "white", borderRadius: 12, border: "1px solid #e2e8f0", padding: "20px 28px", marginBottom: 8 }}>
          {/* Header */}
          <div style={{ marginBottom: 20 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.1em" }}>
              Submission Pipeline
            </span>
          </div>

          {/* Steps + connectors */}
          <div style={{ display: "flex", alignItems: "flex-start", width: "100%" }}>
            {[
              { label: "Doctor Input",   sub: "Clinical note entry",      bg: "#eff6ff", color: "#2563eb", border: "rgba(37,99,235,0.25)",   icon: <UserCircle size={22} /> },
              { label: "Privacy Filter", sub: "vault_ignore.json check",  bg: "#fef2f2", color: "#C8392B", border: "rgba(200,57,43,0.25)",   icon: <ShieldCheck size={22} /> },
              { label: "Redis Queue",    sub: "FIFO by Patient ID",       bg: "#f0fdf4", color: "#16a34a", border: "rgba(22,163,74,0.25)",   icon: <FileText size={22} /> },
              { label: "AI Processing", sub: "FHIR + conflict check",    bg: "#faf5ff", color: "#7c3aed", border: "rgba(124,58,237,0.25)",  icon: <ShieldCheck size={22} /> },
              { label: "Vault Commit",  sub: "AES-256 encrypted",        bg: "#fff7ed", color: "#d97706", border: "rgba(217,119,6,0.25)",   icon: <UploadCloud size={22} /> },
            ].map((step, i, arr) => (
              <React.Fragment key={step.label}>
                {/* Step node */}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, flex: 1, minWidth: 0 }}>
                  <div style={{ width: 52, height: 52, borderRadius: "50%", background: step.bg, border: `2px solid ${step.border}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, color: step.color }}>
                    {step.icon}
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "#0f172a", whiteSpace: "nowrap" }}>{step.label}</div>
                    <div style={{ fontSize: 10, color: "#94a3b8", marginTop: 2, whiteSpace: "nowrap" }}>{step.sub}</div>
                  </div>
                </div>

                {/* CSS triangle arrow between steps */}
                {i < arr.length - 1 && (
                  <div style={{ display: "flex", alignItems: "center", flexShrink: 0, width: 48, marginBottom: 30, paddingTop: 2 }}>
                    <div style={{ flex: 1, height: 2, background: "#e2e8f0" }} />
                    <div style={{ width: 0, height: 0, borderTop: "5px solid transparent", borderBottom: "5px solid transparent", borderLeft: "7px solid #cbd5e1", flexShrink: 0 }} />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        </div>
      </div>

      <style dangerouslySetInnerHTML={{ __html: "@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }" }} />

    </div>
  );
}
