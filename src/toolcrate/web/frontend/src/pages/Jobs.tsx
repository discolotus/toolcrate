import { useSearchParams } from "react-router-dom";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { StatusPill } from "@/components/StatusPill";
import { useCancelJob, useJobs, useRetryJob } from "@/hooks/useJobs";
import type { Job } from "@/api/resources";

const STATES = ["", "pending", "running", "success", "failed", "cancelled"];
const TYPES = ["", "sync_list", "download_track", "library_scan", "recognize_djset"];

export default function Jobs() {
  const [params, setParams] = useSearchParams();
  const state = params.get("state") ?? "";
  const type = params.get("type") ?? "";

  const jobs = useJobs({ state: state || undefined, type: type || undefined, limit: 200 });
  const cancel = useCancelJob();
  const retry = useRetryJob();

  const setFilter = (key: "state" | "type", value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Jobs</h1>
      <FilterRow label="State" value={state} options={STATES} onChange={(v) => setFilter("state", v)} />
      <FilterRow label="Type" value={type} options={TYPES} onChange={(v) => setFilter("type", v)} />
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">ID</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>State</TableHead>
            <TableHead>Progress</TableHead>
            <TableHead>List</TableHead>
            <TableHead className="w-32" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.data?.items.map((j: Job) => (
            <TableRow key={j.id}>
              <TableCell className="font-mono text-xs">{j.id}</TableCell>
              <TableCell className="font-mono text-xs">{j.type}</TableCell>
              <TableCell>
                <StatusPill kind="job" value={j.state} />
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {j.progress_json.total
                  ? `${j.progress_json.current ?? 0} / ${j.progress_json.total}`
                  : j.progress_json.message ?? "—"}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">{j.source_list_id ?? "—"}</TableCell>
              <TableCell>
                {j.state === "running" || j.state === "pending" ? (
                  <Button size="sm" variant="outline" onClick={() => cancel.mutate(j.id)}>
                    Cancel
                  </Button>
                ) : j.state === "failed" ? (
                  <Button size="sm" variant="outline" onClick={() => retry.mutate(j.id)}>
                    Retry
                  </Button>
                ) : null}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function FilterRow({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-muted-foreground">{label}:</span>
      {options.map((opt) => (
        <Button
          key={opt || "all"}
          size="sm"
          variant={value === opt ? "default" : "outline"}
          onClick={() => onChange(opt)}
        >
          {opt || "all"}
        </Button>
      ))}
    </div>
  );
}
