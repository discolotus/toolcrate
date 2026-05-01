import { useParams, Navigate } from "react-router-dom";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrackTable } from "@/components/TrackTable";
import { JobLogPane } from "@/components/JobLogPane";
import { useList, useTriggerSync, usePatchList } from "@/hooks/useLists";
import { useTracks, useRetryTrack } from "@/hooks/useTracks";
import { useJobs } from "@/hooks/useJobs";
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

function ListHistory({ listId }: { listId: number }) {
  const jobs = useJobs({ list_id: listId, limit: 50 });
  const [expanded, setExpanded] = useState<number | null>(null);

  if (!jobs.data) return <div className="text-muted-foreground">Loading…</div>;
  if (jobs.data.items.length === 0) return <div className="text-muted-foreground">No sync history yet.</div>;

  return (
    <ul className="space-y-2">
      {jobs.data.items.map((j) => (
        <li key={j.id} className="rounded-md border border-border">
          <button
            type="button"
            className="flex w-full items-center justify-between px-3 py-2 text-sm hover:bg-accent/40"
            onClick={() => setExpanded(expanded === j.id ? null : j.id)}
          >
            <span>
              <span className="font-mono text-xs">{j.type}</span>
              <span className="ml-2 text-muted-foreground">{j.state}</span>
            </span>
            <span className="text-xs text-muted-foreground">
              {j.started_at ?? j.scheduled_for}
            </span>
          </button>
          {expanded === j.id && (
            <div className="border-t border-border p-3">
              <JobLogPane jobId={j.id} />
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

interface SettingsForm {
  name: string;
  download_path: string;
  sync_interval: string;
  enabled: boolean;
}

function ListSettings({ listId }: { listId: number }) {
  const list = useList(listId);
  const patch = usePatchList(listId);
  const { register, handleSubmit, formState, reset } = useForm<SettingsForm>({
    values: list.data
      ? {
          name: list.data.name,
          download_path: list.data.download_path,
          sync_interval: list.data.sync_interval,
          enabled: list.data.enabled,
        }
      : undefined,
  });

  if (!list.data) return <div className="text-muted-foreground">Loading…</div>;

  const onSubmit = handleSubmit(async (form) => {
    await patch.mutateAsync(form);
    reset(form);
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Settings</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4 max-w-xl" onSubmit={onSubmit}>
          <Field label="Name" id="name">
            <Input id="name" {...register("name", { required: true })} />
          </Field>
          <Field label="Download path" id="download_path">
            <Input id="download_path" {...register("download_path", { required: true })} />
          </Field>
          <Field label="Sync interval" id="sync_interval">
            <select
              id="sync_interval"
              className="h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm"
              {...register("sync_interval")}
            >
              <option value="manual">manual</option>
              <option value="hourly">hourly</option>
              <option value="daily">daily</option>
            </select>
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...register("enabled")} /> Enabled (scheduled syncs)
          </label>
          <div className="flex gap-2">
            <Button type="submit" disabled={!formState.isDirty || patch.isPending}>
              {patch.isPending ? "Saving…" : "Save"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function Field({ label, id, children }: { label: string; id: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-sm" htmlFor={id}>
        {label}
      </label>
      {children}
    </div>
  );
}
