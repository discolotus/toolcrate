import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useCreateList } from "@/hooks/useLists";
import { usePreviewMutation } from "@/hooks/usePreview";
import { ApiError } from "@/api/client";
import type { ListPreview } from "@/api/resources";

const URL_RE = /^https?:\/\/open\.spotify\.com\/playlist\/[A-Za-z0-9]+/;

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const schema = z.object({
  source_url: z.string().regex(URL_RE, "Must be an open.spotify.com playlist URL"),
  name: z.string().min(1, "Required"),
  sync_interval: z.string().min(1),
});
type Form = z.infer<typeof schema>;

export interface AddListDialogProps {
  open: boolean;
  onClose: (created?: { id: number }) => void;
}

export function AddListDialog({ open, onClose }: AddListDialogProps) {
  const { register, handleSubmit, watch, setValue, formState } = useForm<Form>({
    defaultValues: { source_url: "", name: "", sync_interval: "manual" },
  });
  const url = watch("source_url");
  const [preview, setPreview] = useState<ListPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const previewMut = usePreviewMutation();
  const createMut = useCreateList();
  const debounceRef = useRef<number | undefined>(undefined);

  const validUrl = useMemo(() => URL_RE.test(url), [url]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!validUrl) {
      setPreview(null);
      setPreviewError(null);
      return;
    }
    debounceRef.current = window.setTimeout(async () => {
      try {
        const data = await previewMut.mutateAsync(url);
        setPreview(data);
        setPreviewError(null);
        setValue("name", data.name, { shouldValidate: true });
      } catch (e) {
        setPreview(null);
        setPreviewError(e instanceof ApiError ? e.detail ?? e.title ?? "preview failed" : "preview failed");
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, validUrl]);

  const onSubmit = handleSubmit(async (form) => {
    const created = await createMut.mutateAsync({
      name: form.name,
      source_url: form.source_url,
      source_type: "spotify_playlist",
      sync_interval: form.sync_interval,
    });
    onClose({ id: created.id });
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Spotify list</DialogTitle>
        </DialogHeader>
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="space-y-1">
            <label className="text-sm" htmlFor="source_url">
              Playlist URL
            </label>
            <Input id="source_url" autoFocus {...register("source_url")} />
            {previewError && <p className="text-xs text-destructive">{previewError}</p>}
          </div>
          {preview && (
            <div className="rounded-md border border-border p-3 text-sm">
              <div className="font-medium">{preview.name}</div>
              <div className="text-muted-foreground">
                by {preview.owner} · {preview.total_tracks} tracks
              </div>
            </div>
          )}
          <div className="space-y-1">
            <label className="text-sm" htmlFor="name">
              Name
            </label>
            <Input id="name" {...register("name")} />
            {formState.errors.name && <p className="text-xs text-destructive">{formState.errors.name.message}</p>}
          </div>
          <div className="space-y-1">
            <label className="text-sm" htmlFor="sync_interval">
              Sync interval
            </label>
            <select
              id="sync_interval"
              className="h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm"
              {...register("sync_interval")}
            >
              <option value="manual">manual</option>
              <option value="hourly">hourly</option>
              <option value="daily">daily</option>
            </select>
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onClose()}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMut.isPending || !validUrl || !!formState.errors.name}>
              {createMut.isPending ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
