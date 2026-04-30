import { Link } from "react-router-dom";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusPill } from "./StatusPill";
import { fmtRelative } from "@/lib/format";
import type { SourceList } from "@/api/resources";

export function ListMasterTable({ items, selectedId }: { items: SourceList[]; selectedId?: number }) {
  if (items.length === 0) {
    return <div className="rounded-md border border-dashed border-border p-8 text-center text-muted-foreground">No lists yet. Click &ldquo;Add Spotify list&rdquo; to start.</div>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Last sync</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((l) => (
          <TableRow key={l.id} data-state={selectedId === l.id ? "selected" : undefined}>
            <TableCell>
              <Link to={`/app/lists/${l.id}`} className="font-medium hover:underline">
                {l.name}
              </Link>
            </TableCell>
            <TableCell className="text-muted-foreground">{fmtRelative(l.last_synced_at)}</TableCell>
            <TableCell>
              <StatusPill kind="sync" value={l.last_sync_status} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
