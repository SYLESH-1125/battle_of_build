"use client";

export const dynamic = 'force-dynamic';

import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  Shield,
  RefreshCw,
  ChevronDown,
  LogOut,
} from "lucide-react";
import { createClient } from "@/lib/supabase-client";
import StatusBanner from "@/components/StatusBanner";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const API_KEY = process.env.NEXT_PUBLIC_VAULT_API_KEY ?? "vault-test-key-do-not-use-in-production";

interface StagingVaultRecord {
  id: string;
  patient_id: string;
  raw_payload: Record<string, unknown> | null;
  fhir_json: Record<string, unknown> | null;
  status: string;
  processed_at: string;
  conflict_flag?: boolean;
  ai_warning_msg?: string;
  model?: string;
  fallback_reason?: string;
}

export default function AdminPage() {
  const router = useRouter();
  const authClient = createClient();
  const [records, setRecords] = useState<StagingVaultRecord[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<StagingVaultRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState(false);
  const [actionStatus, setActionStatus] = useState<"idle" | "success" | "error">("idle");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [expandedErrors, setExpandedErrors] = useState(false);

  const handleLogout = async () => {
    await authClient.auth.signOut();
    router.push('/');
  };
  const supabaseRef = useRef<ReturnType<typeof createClient> | null>(null);
  // subscriptionRef holds the realtime channel object returned by Supabase.
  // Disable the explicit-any lint rule here because Supabase's channel type
  // is complex and not required for the surrounding logic.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const subscriptionRef = useRef<any>(null);

  // Initialize Supabase client (use shared client from lib), fetch records,
  // and setup real-time subscription — all in one effect so .on() is always
  // called before .subscribe()
  useEffect(() => {
    supabaseRef.current = createClient();

    const fetchAndSubscribe = async () => {
      if (!supabaseRef.current) return;

      try {
        setLoading(true);

        // Fetch pending records (status = pending or processed, not rejected/approved)
        const { data, error } = await supabaseRef.current
          .from("staging_vault")
          .select("*")
          .in("status", ["pending", "processed"])
          .order("processed_at", { ascending: false });

        if (error) {
          console.error("❌ Error fetching records:", error);
        } else {
          console.log("📋 [ADMIN] Loaded records:", data?.length || 0);
          setRecords(data || []);
          if (data && data.length > 0) {
            setSelectedRecord(data[0]);
          }
        }

        // Setup real-time subscription for new records.
        // Remove any existing subscription first to avoid adding callbacks after subscribe().
        if (subscriptionRef.current) {
          try {
            await supabaseRef.current.removeChannel(subscriptionRef.current);
          } catch (err) {
            console.warn("[ADMIN] Failed to remove existing channel:", err);
          }
          subscriptionRef.current = null;
        }

        // Also attempt to remove any other lingering channels that target the staging_vault
        try {
          const existing = (supabaseRef.current as any).getChannels?.() ?? [];
          for (const ch of existing) {
            const topic = ch?.topic ?? ch?.name ?? "";
            if (typeof topic === "string" && topic.includes("staging_vault")) {
              try {
                await supabaseRef.current.removeChannel(ch);
                console.log("[ADMIN] Removed lingering channel:", topic);
              } catch (err) {
                console.warn("[ADMIN] Failed to remove channel:", topic, err);
              }
            }
          }
        } catch (err) {
          console.warn("[ADMIN] Failed to enumerate existing channels:", err);
        }

        // Create a fresh channel (unique name) and attach handlers BEFORE subscribing
        const channel = supabaseRef.current.channel(`staging_vault_changes_${Date.now()}`);

        channel.on(
          "postgres_changes",
          {
            event: "*",
            schema: "public",
            table: "staging_vault",
            filter: `status=in.(pending,processed)`,
          },
          (payload) => {
            console.log("🔔 [ADMIN] Real-time update:", payload.eventType);

            if (payload.eventType === "INSERT") {
              setRecords((prev) => [payload.new as StagingVaultRecord, ...prev]);
            } else if (payload.eventType === "UPDATE") {
              setRecords((prev) =>
                prev.map((r) =>
                  r.id === payload.new.id
                    ? (payload.new as StagingVaultRecord)
                    : r
                )
              );
              if (selectedRecord?.id === payload.new.id) {
                setSelectedRecord(payload.new as StagingVaultRecord);
              }
            } else if (payload.eventType === "DELETE") {
              setRecords((prev) => prev.filter((r) => r.id !== payload.old.id));
              if (selectedRecord?.id === payload.old.id) {
                setSelectedRecord(null);
              }
            }
          }
        );

        try {
          // Subscribe and wait for the subscription to be established.
          // This avoids trying to register handlers after a prior subscribe() call.
          // `subscribe()` returns a Promise-like result in supabase-js v2.
          // eslint-disable-next-line @typescript-eslint/ban-ts-comment
          // @ts-ignore
          await channel.subscribe();
          console.log('[ADMIN] Channel subscribed');
        } catch (err) {
          console.error('[ADMIN] Channel subscribe error', err);
        }

        subscriptionRef.current = channel;
      } catch (error) {
        console.error("Setup error:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAndSubscribe();

    return () => {
      if (subscriptionRef.current) {
        supabaseRef.current?.removeChannel(subscriptionRef.current);
      }
    };
  }, []);

  const handleApprove = async () => {
    if (!selectedRecord) return;

    setActionInProgress(true);
    setActionStatus("idle");
    setActionMessage(null);

    try {
      console.log(`✅ [ADMIN] Approving: ${selectedRecord.id}`);

      const response = await fetch(`${API_BASE}/admin/resolve-pr`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
        },
        body: JSON.stringify({
          staging_id: selectedRecord.id,
          decision: "approve",
          admin_id: "admin-dashboard-user",
          reason: "Approved via admin dashboard",
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setActionStatus("success");
        setActionMessage(`✅ Approved! TX: ${data.tx_id}`);
        setRecords((prev) => prev.filter((r) => r.id !== selectedRecord.id));
        setSelectedRecord(null);
      } else {
        setActionStatus("error");
        setActionMessage(`❌ ${data.detail}`);
      }
    } catch (error) {
      setActionStatus("error");
      setActionMessage(
        `❌ ${error instanceof Error ? error.message : "Unknown error"}`
      );
    } finally {
      setActionInProgress(false);
    }
  };

  const handleReject = async () => {
    if (!selectedRecord) return;

    setActionInProgress(true);
    setActionStatus("idle");
    setActionMessage(null);

    try {
      console.log(`❌ [ADMIN] Rejecting: ${selectedRecord.id}`);

      const response = await fetch(`${API_BASE}/admin/resolve-pr`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
        },
        body: JSON.stringify({
          staging_id: selectedRecord.id,
          decision: "reject",
          admin_id: "admin-dashboard-user",
          reason: selectedRecord.fallback_reason || "Rejected via admin dashboard",
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setActionStatus("success");
        setActionMessage(`✅ Rejected. TX: ${data.tx_id}`);
        setRecords((prev) => prev.filter((r) => r.id !== selectedRecord.id));
        setSelectedRecord(null);
      } else {
        setActionStatus("error");
        setActionMessage(`❌ ${data.detail}`);
      }
    } catch (error) {
      setActionStatus("error");
      setActionMessage(
        `❌ ${error instanceof Error ? error.message : "Unknown error"}`
      );
    } finally {
      setActionInProgress(false);
    }
  };

  const handleManualRefresh = async () => {
    console.log("🔄 Manual refresh triggered");
    setLoading(true);
    try {
      const { data, error } = await supabaseRef.current!
        .from("staging_vault")
        .select("*")
        .in("status", ["pending", "processed"])
        .order("processed_at", { ascending: false });

      if (error) {
        console.error("Error:", error);
      } else {
        console.log("✅ Refreshed:", data?.length || 0);
        setRecords(data || []);
      }
    } finally {
      setLoading(false);
    }
  };

  // Parse error info from ai_warning_msg or fallback_reason
  const parseErrorInfo = (record: StagingVaultRecord) => {
    const messages: string[] = [];
    if (record.ai_warning_msg) messages.push(`⚠️ ${record.ai_warning_msg}`);
    if (record.fallback_reason) messages.push(`🔄 ${record.fallback_reason}`);
    return messages;
  };

  // Derived stats from existing state — no new API calls
  const conflictsCount = records.filter(
    (r) => r.conflict_flag || r.ai_warning_msg
  ).length;
  const redisUnavailableCount = records.filter(
    (r) => r.fallback_reason === "redis_unavailable"
  ).length;

  // ── Change 3: drag-to-resize queue panel state ──────────────
  const [queueWidth, setQueueWidth] = useState(300);
  const isDragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);

  const onDividerMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
    startX.current = e.clientX;
    startWidth.current = queueWidth;
    const onMouseMove = (ev: MouseEvent) => {
      if (!isDragging.current) return;
      const newW = Math.min(520, Math.max(240, startWidth.current + ev.clientX - startX.current));
      setQueueWidth(newW);
    };
    const onMouseUp = () => {
      isDragging.current = false;
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  // ── Change 2: pure-CSS bar chart data ───────────────────────
  const reviewingCount = selectedRecord ? 1 : 0;
  const chartData = [
    { name: "Pending",   value: records.length,    color: "#3b82f6" },
    { name: "Conflicts", value: conflictsCount,     color: "#f59e0b" },
    { name: "Redis",     value: redisUnavailableCount, color: "#8b5cf6" },
    { name: "Reviewing", value: reviewingCount,     color: "#10b981" },
  ];
  const maxVal = Math.max(...chartData.map((d) => d.value), 1);

  return (
    /* ── ROOT: viewport-locked, no page scroll ── */
    <div style={{ height: "100vh", overflow: "hidden", display: "flex", flexDirection: "column", background: "#f8fafc" }}>

      {/* ── TOPBAR — fixed height 56px, never shrinks ── */}
      <div
        style={{
          flexShrink: 0,
          height: 56,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 28px",
          background: "white",
          borderBottom: "1px solid #e2e8f0",
          zIndex: 50,
          overflow: "hidden",
        }}
      >
        {/* Left: logo + title */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, background: "#16a34a", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}>
              <Shield size={14} />
            </div>
            <span style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", letterSpacing: "-0.01em" }}>DHMV</span>
          </div>
          <div style={{ width: 1, height: 20, background: "#e2e8f0" }} />
          <div>
            <p style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em", color: "#94a3b8", margin: 0, lineHeight: 1 }}>
              Module 4 — Admin Triage
            </p>
            <h1 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", margin: "2px 0 0 0", lineHeight: 1 }}>
              Clinical Record Review Queue
            </h1>
          </div>
        </div>

        {/* Right: actions only */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            onClick={handleManualRefresh}
            disabled={loading}
            title="Refresh"
            style={{ width: 32, height: 32, borderRadius: 8, border: "1px solid #e2e8f0", background: "white", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", cursor: "pointer" }}
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          <button
            onClick={handleLogout}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 14px", borderRadius: 6, border: "1px solid #e2e8f0", background: "transparent", fontSize: 13, fontWeight: 500, color: "#64748b", cursor: "pointer" }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "#fef2f2"; e.currentTarget.style.borderColor = "#fca5a5"; e.currentTarget.style.color = "#dc2626"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.color = "#64748b"; }}
          >
            <LogOut size={13} />
            Logout
          </button>
          <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#1e293b", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, color: "white" }}>
            A
          </div>
        </div>
      </div>

      {/* ── SCROLLABLE CONTENT AREA — only this scrolls ── */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", padding: "20px 28px", gap: 20 }}>

        {/* ── SPLIT PANEL — fixed 580px, never grows ── */}
        <div
          style={{
            height: 580,
            flexShrink: 0,
            display: "flex",
            borderRadius: 12,
            border: "1px solid #e2e8f0",
            background: "white",
            overflow: "hidden",
          }}
        >

          {/* A) QUEUE PANEL — fixed width, internal scroll */}
          <div
            style={{
              width: queueWidth,
              minWidth: 240,
              maxWidth: 520,
              flexShrink: 0,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              borderRight: "1px solid #e2e8f0",
              background: "#fafafa",
            }}
          >
            {/* A1: Queue header — fixed, does not scroll */}
            <div
              style={{
                flexShrink: 0,
                padding: "14px 16px",
                borderBottom: "1px solid #e2e8f0",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: "white",
              }}
            >
              <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#64748b" }}>
                Pending Queue
              </span>
              <span style={{ background: "#0f172a", color: "white", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 20 }}>
                {records.length}
              </span>
            </div>

            {/* A2: Queue list — scrolls internally */}
            <div style={{ flex: 1, overflowY: "auto", overflowX: "hidden" }}>
              {loading ? (
                <>
                  {[...Array(5)].map((_, i) => (
                    <div key={i} style={{ borderBottom: "1px solid #f1f5f9", padding: "12px 16px" }}>
                      <div style={{ height: 10, width: "70%", borderRadius: 4, background: "#e2e8f0", animation: "pulse 1.5s infinite" }} />
                      <div style={{ height: 8, width: "45%", borderRadius: 4, background: "#f1f5f9", marginTop: 8, animation: "pulse 1.5s infinite" }} />
                    </div>
                  ))}
                </>
              ) : records.length === 0 ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 8, color: "#94a3b8" }}>
                  <CheckCircle size={26} style={{ color: "#86efac" }} />
                  <p style={{ fontSize: 13, fontWeight: 600, color: "#475569", margin: 0 }}>Queue Empty</p>
                  <p style={{ fontSize: 11, margin: 0 }}>All records reviewed</p>
                </div>
              ) : (
                records.map((record) => {
                  const initials = record.patient_id.slice(0, 2).toUpperCase();
                  const isSelected = selectedRecord?.id === record.id;
                  const hasWarning = !!(record.ai_warning_msg || record.conflict_flag);
                  const hasRedis = record.fallback_reason === "redis_unavailable";

                  return (
                    <div
                      key={record.id}
                      onClick={() => setSelectedRecord(record)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "10px 14px",
                        borderBottom: "1px solid #f1f5f9",
                        borderLeft: isSelected ? "3px solid #16a34a" : "3px solid transparent",
                        background: isSelected ? "#f0fdf4" : "transparent",
                        cursor: "pointer",
                        transition: "background 0.12s",
                      }}
                      onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = "#f8fafc"; }}
                      onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
                    >
                      {/* Initials circle */}
                      <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#e0f2fe", color: "#0369a1", fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        {initials}
                      </div>

                      {/* Info */}
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <p style={{ fontSize: 12, fontWeight: 600, color: "#0f172a", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {record.patient_id}
                        </p>
                        <p style={{ fontSize: 10, color: "#94a3b8", margin: "2px 0 0 0", display: "flex", alignItems: "center", gap: 3 }}>
                          <Clock size={9} />
                          {record.processed_at ? new Date(record.processed_at).toLocaleTimeString() : "—"}
                        </p>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 3, marginTop: 4 }}>
                          {hasWarning && (
                            <span style={{ fontSize: 9, fontWeight: 500, background: "#fef3c7", color: "#92400e", padding: "1px 5px", borderRadius: 3 }}>⚠ rule-based</span>
                          )}
                          {hasRedis && (
                            <span style={{ fontSize: 9, fontWeight: 500, background: "#e0e7ff", color: "#3730a3", padding: "1px 5px", borderRadius: 3 }}>redis</span>
                          )}
                          {record.conflict_flag && (
                            <span style={{ fontSize: 9, fontWeight: 500, background: "#fee2e2", color: "#991b1b", padding: "1px 5px", borderRadius: 3 }}>conflict</span>
                          )}
                        </div>
                      </div>

                      {/* Quick-action icons */}
                      <div style={{ display: "flex", flexDirection: "column", gap: 4, flexShrink: 0 }}>
                        <button
                          onClick={(e) => { e.stopPropagation(); setSelectedRecord(record); handleApprove(); }}
                          disabled={actionInProgress || record.status !== "processed"}
                          title="Quick Approve"
                          style={{ width: 24, height: 24, borderRadius: "50%", border: "none", background: "#dcfce7", color: "#16a34a", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", opacity: (actionInProgress || record.status !== "processed") ? 0.3 : 1 }}
                        >
                          <CheckCircle size={12} />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); setSelectedRecord(record); handleReject(); }}
                          disabled={actionInProgress}
                          title="Quick Reject"
                          style={{ width: 24, height: 24, borderRadius: "50%", border: "none", background: "#fee2e2", color: "#dc2626", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", opacity: actionInProgress ? 0.3 : 1 }}
                        >
                          <XCircle size={12} />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* B) DRAG DIVIDER */}
          <div
            onMouseDown={onDividerMouseDown}
            style={{ width: 4, flexShrink: 0, background: "#e2e8f0", cursor: "col-resize", transition: "background 0.15s" }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#94a3b8")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#e2e8f0")}
          />

          {/* C) DETAIL PANEL */}
          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            {!selectedRecord ? (
              /* Empty state */
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, color: "#94a3b8" }}>
                <Shield size={52} style={{ color: "#e2e8f0" }} />
                <p style={{ fontSize: 14, textAlign: "center", margin: 0 }}>
                  Select a record from the queue to review
                </p>
              </div>
            ) : (
              <>
                {/* C1: Scrollable content */}
                <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 14 }}>

                  {/* Detail header */}
                  <div>
                    <h2 style={{ fontSize: 17, fontWeight: 700, color: "#0f172a", margin: 0 }}>
                      Patient: {selectedRecord.patient_id}
                    </h2>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 5, background: "#eff6ff", color: "#1d4ed8", fontSize: 11, fontWeight: 500, padding: "4px 10px", borderRadius: 6 }}>
                        <Clock size={11} />
                        {new Date(selectedRecord.processed_at).toLocaleString()}
                      </span>
                      <span style={{ display: "inline-flex", alignItems: "center", background: "#f5f3ff", color: "#6d28d9", fontSize: 11, fontWeight: 500, padding: "4px 10px", borderRadius: 6 }}>
                        Model: {selectedRecord.model || "unknown"}
                      </span>
                      {selectedRecord.conflict_flag && (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 5, background: "#fef2f2", color: "#b91c1c", fontSize: 11, fontWeight: 500, padding: "4px 10px", borderRadius: 6 }}>
                          <AlertCircle size={11} />
                          Conflict Detected
                        </span>
                      )}
                      {selectedRecord.status === "processed" && (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 5, background: "#f0fdf4", color: "#15803d", fontSize: 11, fontWeight: 500, padding: "4px 10px", borderRadius: 6 }}>
                          ✅ Processed &amp; Ready
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Warning box */}
                  {(selectedRecord.ai_warning_msg || selectedRecord.fallback_reason) && (
                    <div style={{ borderRadius: 8, border: "1px solid #fcd34d", background: "#fffbeb", padding: "12px 16px" }}>
                      <button
                        onClick={() => setExpandedErrors(!expandedErrors)}
                        style={{ display: "flex", width: "100%", alignItems: "center", justifyContent: "space-between", background: "none", border: "none", cursor: "pointer", padding: 0 }}
                      >
                        <span style={{ fontSize: 13, fontWeight: 600, color: "#92400e" }}>⚠️ Processing Issues</span>
                        <ChevronDown size={14} style={{ color: "#b45309", transform: expandedErrors ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
                      </button>
                      {expandedErrors && (
                        <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid #fde68a", display: "flex", flexDirection: "column", gap: 6 }}>
                          {selectedRecord.ai_warning_msg && (
                            <p style={{ fontSize: 13, color: "#92400e", margin: 0 }}>
                              <strong>AI Warning:</strong> {selectedRecord.ai_warning_msg}
                            </p>
                          )}
                          {selectedRecord.fallback_reason && (
                            <p style={{ fontSize: 13, color: "#92400e", margin: 0 }}>
                              <strong>Fallback Reason:</strong> {selectedRecord.fallback_reason}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Before / After code panels */}
                  <div>
                    <p style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "#94a3b8", margin: "0 0 10px 0" }}>
                      Before / After Clinical Data
                    </p>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                      <div style={{ borderRadius: 8, background: "#0f172a", padding: 14 }}>
                        <p style={{ fontSize: 11, fontWeight: 600, color: "#64748b", margin: "0 0 8px 0" }}>📥 Input (Raw)</p>
                        <pre style={{ fontSize: 11, color: "#cbd5e1", fontFamily: "monospace", whiteSpace: "pre-wrap", wordBreak: "break-all", margin: 0, maxHeight: 220, overflowY: "auto" }}>
                          {selectedRecord.raw_payload ? JSON.stringify(selectedRecord.raw_payload, null, 2) : "(empty)"}
                        </pre>
                      </div>
                      <div style={{ borderRadius: 8, background: "#0f172a", padding: 14 }}>
                        <p style={{ fontSize: 11, fontWeight: 600, color: "#64748b", margin: "0 0 8px 0" }}>📤 Output (FHIR)</p>
                        <pre style={{ fontSize: 11, color: "#6ee7b7", fontFamily: "monospace", whiteSpace: "pre-wrap", wordBreak: "break-all", margin: 0, maxHeight: 220, overflowY: "auto" }}>
                          {selectedRecord.fhir_json ? JSON.stringify(selectedRecord.fhir_json, null, 2) : "(empty or processing)"}
                        </pre>
                      </div>
                    </div>
                  </div>

                  {/* Status banner */}
                  {actionStatus !== "idle" && (
                    <StatusBanner
                      variant={actionStatus}
                      title={actionStatus === "success" ? "Action Successful" : "Action Failed"}
                      description={actionMessage || ""}
                    />
                  )}
                </div>

                {/* C2: Action buttons — fixed at bottom, never scrolls away */}
                <div style={{ flexShrink: 0, padding: "14px 24px", borderTop: "1px solid #e2e8f0", background: "white", display: "flex", gap: 12 }}>
                  <button
                    onClick={handleApprove}
                    disabled={actionInProgress || selectedRecord.status !== "processed"}
                    style={{ flex: 1, height: 42, borderRadius: 8, border: "none", background: "#16a34a", color: "white", fontSize: 14, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, opacity: (actionInProgress || selectedRecord.status !== "processed") ? 0.5 : 1 }}
                  >
                    {actionInProgress ? "Processing…" : <><CheckCircle size={16} /> Approve &amp; Commit</>}
                  </button>
                  <button
                    onClick={handleReject}
                    disabled={actionInProgress}
                    style={{ flex: 1, height: 42, borderRadius: 8, border: "none", background: "#dc2626", color: "white", fontSize: 14, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, opacity: actionInProgress ? 0.5 : 1 }}
                  >
                    {actionInProgress ? "Processing…" : <><XCircle size={16} /> Reject</>}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* ── CHART CARD — after split panel, visible on scroll ── */}
        <div style={{ flexShrink: 0, background: "white", borderRadius: 12, border: "1px solid #e2e8f0", padding: "24px 32px", marginBottom: 8 }}>

          {/* Chart header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 600, color: "#0f172a", margin: 0 }}>Queue Statistics</h2>
              <p style={{ fontSize: 12, color: "#94a3b8", margin: "4px 0 0 0" }}>Live counts from staging vault</p>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              {chartData.map((d) => (
                <div key={d.name} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: d.color, display: "inline-block" }} />
                  <span style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>{d.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* CSS bar chart */}
          <div style={{ position: "relative" }}>

            {/* Y-axis gridlines */}
            {[0, 25, 50, 75, 100].map((pct) => {
              const val = Math.round((pct / 100) * maxVal);
              return (
                <div key={pct} style={{ position: "absolute", left: 40, right: 0, bottom: 64 + (pct / 100) * 168, borderTop: "1px dashed #f1f5f9", pointerEvents: "none" }}>
                  <span style={{ position: "absolute", left: -38, top: -8, fontSize: 10, color: "#94a3b8", whiteSpace: "nowrap" }}>{val}</span>
                </div>
              );
            })}

            {/* Bars */}
            <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-around", height: 210, paddingLeft: 40, borderBottom: "2px solid #e2e8f0" }}>
              {chartData.map((d) => {
                const barH = Math.max(6, (d.value / maxVal) * 168);
                return (
                  <div key={d.name} style={{ flex: 1, maxWidth: 120, display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{ width: "55%", height: barH, background: d.color, borderRadius: "6px 6px 0 0", transition: "height 0.4s ease" }} />
                  </div>
                );
              })}
            </div>

            {/* Labels + values below bars */}
            <div style={{ display: "flex", justifyContent: "space-around", paddingLeft: 40, paddingTop: 14 }}>
              {chartData.map((d) => (
                <div key={d.name} style={{ flex: 1, maxWidth: 120, textAlign: "center" }}>
                  <span style={{ fontSize: 22, fontWeight: 700, color: d.color, display: "block", lineHeight: 1.2 }}>{d.value}</span>
                  <span style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>{d.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
