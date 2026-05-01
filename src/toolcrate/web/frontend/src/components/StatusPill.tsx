import { Badge, type BadgeProps } from "@/components/ui/badge";

const SYNC_VARIANT: Record<string, BadgeProps["variant"]> = {
  ok: "success",
  error: "destructive",
  never: "secondary",
};

const TRACK_VARIANT: Record<string, BadgeProps["variant"]> = {
  done: "success",
  downloading: "default",
  queued: "secondary",
  pending: "outline",
  failed: "destructive",
  skipped: "secondary",
};

const JOB_VARIANT: Record<string, BadgeProps["variant"]> = {
  success: "success",
  running: "default",
  pending: "secondary",
  failed: "destructive",
  cancelled: "outline",
};

const VARIANTS = { sync: SYNC_VARIANT, track: TRACK_VARIANT, job: JOB_VARIANT };

export function StatusPill({ kind, value }: { kind: keyof typeof VARIANTS; value: string }) {
  const variant = VARIANTS[kind][value] ?? "outline";
  return <Badge variant={variant}>{value}</Badge>;
}
