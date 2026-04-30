import type { QueryClient } from "@tanstack/react-query";
import { queryKeys } from "./keys";

export interface SseEvent {
  name: string;
  data: unknown;
}

export function dispatchSseEvent(client: QueryClient, event: SseEvent): void {
  const payload = (event.data ?? {}) as { id?: number; source_list_id?: number };
  switch (event.name) {
    case "list.created":
    case "list.deleted":
      client.invalidateQueries({ queryKey: queryKeys.lists.all });
      return;
    case "list.updated":
      client.invalidateQueries({ queryKey: queryKeys.lists.all });
      if (payload.id !== undefined) {
        client.invalidateQueries({ queryKey: queryKeys.lists.byId(payload.id) });
      }
      return;
    case "job.created":
    case "job.update":
    case "job.finished":
      client.invalidateQueries({ queryKey: queryKeys.jobs.all });
      if (payload.source_list_id !== undefined) {
        client.invalidateQueries({ queryKey: queryKeys.lists.byId(payload.source_list_id) });
        client.invalidateQueries({ queryKey: queryKeys.tracks(payload.source_list_id) });
      }
      return;
    case "track.updated":
      if (payload.source_list_id !== undefined) {
        client.invalidateQueries({ queryKey: queryKeys.tracks(payload.source_list_id) });
      }
      return;
    default:
      return;
  }
}

export interface LogEvent {
  job_id: number;
  line: string;
  ts: string;
}

export function isLogAppend(event: SseEvent): event is { name: "log.append"; data: LogEvent } {
  return event.name === "log.append";
}
