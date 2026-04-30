import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import type { ListPreview } from "@/api/resources";

export function usePreviewMutation() {
  return useMutation({
    mutationFn: (source_url: string) =>
      apiFetch<ListPreview>("/api/v1/lists/preview", {
        method: "POST",
        body: JSON.stringify({ source_url }),
      }),
  });
}
