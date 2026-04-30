import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { dispatchSseEvent, isLogAppend, type SseEvent } from "@/api/sse";

type LogListener = (line: string, ts: string) => void;
const logListeners: Map<number, Set<LogListener>> = new Map();

export function subscribeJobLog(jobId: number, listener: LogListener): () => void {
  let bucket = logListeners.get(jobId);
  if (!bucket) {
    bucket = new Set();
    logListeners.set(jobId, bucket);
  }
  bucket.add(listener);
  return () => {
    bucket?.delete(listener);
    if (bucket && bucket.size === 0) logListeners.delete(jobId);
  };
}

export function useSseInvalidation(): { live: boolean } {
  const queryClient = useQueryClient();
  const [live, setLive] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);
  const retryRef = useRef(0);

  useEffect(() => {
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const es = new EventSource("/api/v1/events");
      sourceRef.current = es;

      es.onopen = () => {
        retryRef.current = 0;
        setLive(true);
      };
      es.onerror = () => {
        setLive(false);
        es.close();
        if (cancelled) return;
        const delay = Math.min(30_000, 500 * 2 ** retryRef.current++);
        setTimeout(connect, delay);
      };

      const handle = (name: string, data: unknown) => {
        const event: SseEvent = { name, data };
        dispatchSseEvent(queryClient, event);
        if (isLogAppend(event)) {
          const log = event.data;
          const bucket = logListeners.get(log.job_id);
          bucket?.forEach((l) => l(log.line, log.ts));
        }
      };

      const wire = (name: string) =>
        es.addEventListener(name, (msg) => {
          try {
            handle(name, JSON.parse((msg as MessageEvent<string>).data));
          } catch {
            handle(name, undefined);
          }
        });

      [
        "list.created",
        "list.updated",
        "list.deleted",
        "job.created",
        "job.update",
        "job.finished",
        "track.updated",
        "log.append",
      ].forEach(wire);
    };

    connect();
    return () => {
      cancelled = true;
      sourceRef.current?.close();
    };
  }, [queryClient]);

  return { live };
}
