import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { queryKeys } from "@/api/keys";
import type { Job, Page } from "@/api/resources";

export interface JobFilter {
  state?: string;
  type?: string;
  list_id?: number;
  limit?: number;
  offset?: number;
}

export function useJobs(filter: JobFilter = {}) {
  const params = new URLSearchParams();
  Object.entries(filter).forEach(([k, v]) => v !== undefined && v !== "" && params.set(k, String(v)));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return useQuery({
    queryKey: queryKeys.jobs.list(filter as Record<string, unknown>),
    queryFn: () => apiFetch<Page<Job>>(`/api/v1/jobs${qs}`),
  });
}

export function useJob(id: number) {
  return useQuery({
    queryKey: queryKeys.jobs.byId(id),
    queryFn: () => apiFetch<Job>(`/api/v1/jobs/${id}`),
  });
}

export function useCancelJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<Job>(`/api/v1/jobs/${id}/cancel`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
  });
}

export function useRetryJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiFetch<Job>(`/api/v1/jobs/${id}/retry`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.jobs.all }),
  });
}
