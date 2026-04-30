import { Link } from "react-router-dom";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { useLists } from "@/hooks/useLists";
import { useJobs } from "@/hooks/useJobs";
import { fmtRelative } from "@/lib/format";

export default function Dashboard() {
  const lists = useLists();
  const activeJobs = useJobs({ state: "running", limit: 50 });
  const pendingJobs = useJobs({ state: "pending", limit: 50 });
  const recentJobs = useJobs({ limit: 10 });

  const totalLists = lists.data?.total ?? 0;
  const activeCount = (activeJobs.data?.total ?? 0) + (pendingJobs.data?.total ?? 0);

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle>Lists</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-semibold">{totalLists}</div>
          <Link to="/app/sources/spotify" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
            Manage Spotify lists
          </Link>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active jobs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-semibold">{activeCount}</div>
          <Link to="/app/jobs?state=running" className="text-sm text-muted-foreground underline-offset-4 hover:underline">
            View running jobs
          </Link>
        </CardContent>
      </Card>

      <Card className="md:col-span-3">
        <CardHeader>
          <CardTitle>Recent activity</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {recentJobs.data?.items.length ? (
            <ul className="divide-y divide-border">
              {recentJobs.data.items.map((j) => (
                <li key={j.id} className="flex items-center justify-between py-2">
                  <span className="font-mono text-xs">{j.type}</span>
                  <span className="text-muted-foreground">{j.state}</span>
                  <span className="text-muted-foreground">{fmtRelative(j.finished_at ?? j.started_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-muted-foreground">No recent activity yet.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
