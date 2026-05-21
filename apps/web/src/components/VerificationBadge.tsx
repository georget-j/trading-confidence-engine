import type { VerificationStatus } from "@/lib/types";

const STYLES: Record<VerificationStatus, { label: string; classes: string }> = {
  verified: {
    label: "Verified",
    classes: "bg-emerald-100 text-emerald-900 ring-emerald-300",
  },
  partially_verified: {
    label: "Partially verified",
    classes: "bg-amber-100 text-amber-900 ring-amber-300",
  },
  not_verified: {
    label: "Not verified",
    classes: "bg-rose-100 text-rose-900 ring-rose-300",
  },
};

export function VerificationBadge({ status }: { status: VerificationStatus }) {
  const s = STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${s.classes}`}
    >
      <span className="h-2 w-2 rounded-full bg-current opacity-70" />
      {s.label}
    </span>
  );
}
