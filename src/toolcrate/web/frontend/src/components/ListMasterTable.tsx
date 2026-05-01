import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusPill } from "./StatusPill";
import { fmtRelative } from "@/lib/format";
import { artUrl, totalTracksRemote, type SourceList } from "@/api/resources";

interface Props {
  items: SourceList[];
  selectedId?: number;
  onSelect?: (id: number) => void;
}

export function ListMasterTable({ items, selectedId, onSelect }: Props) {
  if (items.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-8 text-center text-muted-foreground">
        No lists yet. Click &ldquo;Add Spotify list&rdquo; to start.
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-10" />
          <TableHead>Name</TableHead>
          <TableHead className="w-16 text-right">Tracks</TableHead>
          <TableHead>Last sync</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((l) => {
          const art = artUrl(l);
          const count = totalTracksRemote(l);
          return (
            <TableRow
              key={l.id}
              data-state={selectedId === l.id ? "selected" : undefined}
              className="cursor-pointer"
              onClick={() => onSelect?.(l.id)}
            >
              <TableCell className="pr-0">
                {art ? (
                  <img
                    src={art}
                    alt=""
                    className="h-8 w-8 rounded object-cover"
                  />
                ) : (
                  <div className="h-8 w-8 rounded bg-muted" />
                )}
              </TableCell>
              <TableCell className="font-medium">{l.name}</TableCell>
              <TableCell className="text-right text-muted-foreground">
                {count ?? "—"}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {fmtRelative(l.last_synced_at)}
              </TableCell>
              <TableCell>
                <StatusPill kind="sync" value={l.last_sync_status} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
