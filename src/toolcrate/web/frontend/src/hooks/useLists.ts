import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { queryKeys } from "@/api/keys";
import type { Page, SourceList } from "@/api/resources";

export function useLists(filter: { source_type?: string } = {}) {
  const qs = filter.source_type ? `?source_type=${encodeURIComponent(filter.source_type)}` : "";
  return useQuery({
    queryKey: [...queryKeys.lists.all, filter],
    queryFn: () => apiFetch<Page<SourceList>>(`/api/v1/lists${qs}`),
  });
}

export function useList(id: number) {
  return useQuery({
    queryKey: queryKeys.lists.byId(id),
    queryFn: () => apiFetch<SourceList>(`/api/v1/lists/${id}`),
  });
}

export function useCreateList() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; source_url: string; source_type?: string; sync_interval?: string }) =>
      apiFetch<SourceList>("/api/v1/lists", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.lists.all }),
  });
}

export function usePatchList(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<Pick<SourceList, "name" | "download_path" | "sync_interval" | "enabled">>) =>
      apiFetch<SourceList>(`/api/v1/lists/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.lists.all });
      qc.invalidateQueries({ queryKey: queryKeys.lists.byId(id) });
    },
  });
}

export function useTriggerSync(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ job_id: number }>(`/api/v1/lists/${id}/sync`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
  });
}
