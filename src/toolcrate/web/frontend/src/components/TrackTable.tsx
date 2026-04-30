import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusPill } from "./StatusPill";
import { Button } from "@/components/ui/button";
import { fmtDuration } from "@/lib/format";
import type { TrackEntry } from "@/api/resources";

export function TrackTable({ items, onRetry }: { items: TrackEntry[]; onRetry: (id: number) => void }) {
  if (items.length === 0) {
    return <div className="rounded-md border border-dashed border-border p-8 text-center text-muted-foreground">No tracks yet. Trigger a sync to populate.</div>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">#</TableHead>
          <TableHead>Artist</TableHead>
          <TableHead>Title</TableHead>
          <TableHead className="w-20">Duration</TableHead>
          <TableHead className="w-28">Status</TableHead>
          <TableHead className="w-24" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((t) => (
          <TableRow key={t.id}>
            <TableCell className="text-muted-foreground">{t.position}</TableCell>
            <TableCell>{t.artist ?? "—"}</TableCell>
            <TableCell className="font-medium">{t.title ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">{fmtDuration(t.duration_sec)}</TableCell>
            <TableCell>
              <StatusPill kind="track" value={t.download_status} />
            </TableCell>
            <TableCell>
              {(t.download_status === "failed" || t.download_status === "skipped" || t.download_status === "pending") && (
                <Button size="sm" variant="outline" onClick={() => onRetry(t.id)}>
                  Retry
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
