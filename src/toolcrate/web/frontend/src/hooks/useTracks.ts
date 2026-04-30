import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { queryKeys } from "@/api/keys";
import type { Page, TrackEntry } from "@/api/resources";

export function useTracks(listId: number, status?: string) {
  const qs = status ? `?status=${encodeURIComponent(status)}&limit=2000` : "?limit=2000";
  return useQuery({
    queryKey: queryKeys.tracks(listId, status),
    queryFn: () => apiFetch<Page<TrackEntry>>(`/api/v1/lists/${listId}/tracks${qs}`),
    enabled: Number.isFinite(listId),
  });
}

export function useRetryTrack(listId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trackId: number) =>
      apiFetch<{ job_id: number }>(`/api/v1/lists/${listId}/tracks/${trackId}/download`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.tracks(listId) });
      qc.invalidateQueries({ queryKey: queryKeys.jobs.all });
    },
  });
}

export function useSkipTrack(listId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (trackId: number) =>
      apiFetch<TrackEntry>(`/api/v1/lists/${listId}/tracks/${trackId}/skip`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.tracks(listId) }),
  });
}
