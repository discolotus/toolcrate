import { useParams, Navigate } from "react-router-dom";
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { TrackTable } from "@/components/TrackTable";
import { useList, useTriggerSync } from "@/hooks/useLists";
import { useTracks, useRetryTrack } from "@/hooks/useTracks";
import { fmtRelative } from "@/lib/format";
import { StatusPill } from "@/components/StatusPill";

const STATUS_OPTIONS = ["", "pending", "queued", "downloading", "done", "failed", "skipped"];

export default function ListDetail() {
  const { id } = useParams();
  const numericId = id ? Number(id) : NaN;
  if (!Number.isFinite(numericId)) return <Navigate to="/app/sources/spotify" replace />;

  return <ListDetailInner listId={numericId} />;
}

function ListDetailInner({ listId }: { listId: number }) {
  const list = useList(listId);
  const [statusFilter, setStatusFilter] = useState("");
  const tracks = useTracks(listId, statusFilter || undefined);
  const sync = useTriggerSync(listId);
  const retry = useRetryTrack(listId);

  if (list.isLoading) return <div>Loading…</div>;
  if (list.error || !list.data) return <div className="text-destructive">List not found.</div>;

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{list.data.name}</h1>
          <p className="text-sm text-muted-foreground">
            Last sync {fmtRelative(list.data.last_synced_at)} · <StatusPill kind="sync" value={list.data.last_sync_status} />
          </p>
        </div>
        <Button onClick={() => sync.mutate()} disabled={sync.isPending}>
          {sync.isPending ? "Queuing…" : "Sync now"}
        </Button>
      </header>
      <Tabs defaultValue="tracks">
        <TabsList>
          <TabsTrigger value="tracks">Tracks</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>
        <TabsContent value="tracks" className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((opt) => (
              <Button
                key={opt || "all"}
                size="sm"
                variant={statusFilter === opt ? "default" : "outline"}
                onClick={() => setStatusFilter(opt)}
              >
                {opt || "all"}
              </Button>
            ))}
          </div>
          <TrackTable items={tracks.data?.items ?? []} onRetry={(tid) => retry.mutate(tid)} />
        </TabsContent>
        <TabsContent value="history">
          <ListHistory listId={listId} />
        </TabsContent>
        <TabsContent value="settings">
          <ListSettings listId={listId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// History + Settings filled in by Task 16.
function ListHistory({ listId: _listId }: { listId: number }) {
  return <div className="text-muted-foreground">History tab — filled in by the next task.</div>;
}
function ListSettings({ listId: _listId }: { listId: number }) {
  return <div className="text-muted-foreground">Settings tab — filled in by the next task.</div>;
}
