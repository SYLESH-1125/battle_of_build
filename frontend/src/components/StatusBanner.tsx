"use client";

import React from "react";
import { AlertTriangle, CheckCircle2, Loader2, ShieldAlert } from "lucide-react";

export type StatusVariant = "submitting" | "success" | "blocked" | "error";

const variantStyles: Record<
  StatusVariant,
  { container: string; icon: React.ElementType; iconClass: string }
> = {
  submitting: {
    container: "border-slate-200 bg-slate-50",
    icon: Loader2,
    iconClass: "text-slate-600 animate-spin",
  },
  success: {
    container: "border-emerald-200 bg-emerald-50",
    icon: CheckCircle2,
    iconClass: "text-emerald-600",
  },
  blocked: {
    container: "border-amber-200 bg-amber-50",
    icon: ShieldAlert,
    iconClass: "text-amber-600",
  },
  error: {
    container: "border-rose-200 bg-rose-50",
    icon: AlertTriangle,
    iconClass: "text-rose-600",
  },
};

type StatusBannerProps = {
  variant: StatusVariant;
  title: string;
  description?: string | null;
};

export default function StatusBanner({
  variant,
  title,
  description,
}: StatusBannerProps) {
  const style = variantStyles[variant];
  const Icon = style.icon;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-start gap-3 rounded-2xl border px-4 py-3 ${style.container}`}
    >
      <Icon className={`mt-0.5 ${style.iconClass}`} size={20} />
      <div className="space-y-1">
        <p className="text-sm font-semibold text-slate-900">{title}</p>
        {description ? (
          <p className="text-sm text-slate-600">{description}</p>
        ) : null}
      </div>
    </div>
  );
}
