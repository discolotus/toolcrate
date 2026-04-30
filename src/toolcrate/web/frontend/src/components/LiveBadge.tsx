import { Badge } from "@/components/ui/badge";

export function LiveBadge({ live }: { live: boolean }) {
  return (
    <Badge variant={live ? "success" : "warning"} className="text-[10px] uppercase tracking-wider">
      {live ? "live" : "reconnecting"}
    </Badge>
  );
}
