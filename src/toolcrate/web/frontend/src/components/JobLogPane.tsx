import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/api/client";
import { subscribeJobLog } from "@/hooks/useSseInvalidation";

export function JobLogPane({ jobId }: { jobId: number }) {
  const [lines, setLines] = useState<string[]>([]);
  const [follow, setFollow] = useState(true);
  const ref = useRef<HTMLPreElement | null>(null);
  const offsetRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    setLines([]);
    offsetRef.current = 0;

    const loadInitial = async () => {
      try {
        const page = await apiFetch<{ lines: string[]; next_offset: number | null }>(
          `/api/v1/jobs/${jobId}/log?limit=2000`,
        );
        if (cancelled) return;
        setLines(page.lines);
        offsetRef.current = page.lines.length;
      } catch {
        // 404 etc. — fall through to the SSE feed
      }
    };
    loadInitial();

    const unsub = subscribeJobLog(jobId, (line) => {
      setLines((prev) => prev.concat(line));
    });

    return () => {
      cancelled = true;
      unsub();
    };
  }, [jobId]);

  useEffect(() => {
    if (follow && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [lines, follow]);

  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <Button size="sm" variant={follow ? "default" : "outline"} onClick={() => setFollow((f) => !f)}>
          {follow ? "Following" : "Paused"}
        </Button>
      </div>
      <pre
        ref={ref}
        className="max-h-96 overflow-auto rounded-md border border-border bg-card p-3 font-mono text-xs leading-snug"
      >
        {lines.join("\n") || "(no log yet)"}
      </pre>
    </div>
  );
}
