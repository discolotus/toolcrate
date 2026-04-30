// Manually-curated DTOs to keep pages decoupled from generated types.
// Refresh by hand when /api/openapi.json changes; the types in src/api/types.ts
// remain the source of truth for compile-time checking elsewhere.

export interface SourceList {
  id: number;
  name: string;
  source_type: "spotify_playlist" | "youtube_djset" | "manual";
  source_url: string;
  external_id: string;
  download_path: string;
  enabled: boolean;
  sync_interval: string;
  last_synced_at: string | null;
  last_sync_status: string;
  last_error: string | null;
  oauth_account_id: number | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TrackEntry {
  id: number;
  source_list_id: number;
  position: number;
  artist: string | null;
  title: string | null;
  album: string | null;
  duration_sec: number | null;
  isrc: string | null;
  spotify_track_id: string | null;
  download_status: "pending" | "queued" | "downloading" | "done" | "failed" | "skipped";
  first_seen_at: string;
  last_seen_at: string;
}

export interface Job {
  id: number;
  type: "sync_list" | "recognize_djset" | "download_track" | "library_scan";
  state: "pending" | "running" | "success" | "failed" | "cancelled";
  priority: number;
  source_list_id: number | null;
  attempts: number;
  max_attempts: number;
  scheduled_for: string;
  started_at: string | null;
  finished_at: string | null;
  progress_json: { current?: number; total?: number; message?: string };
  error: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ListPreview {
  source_type: "spotify_playlist";
  external_id: string;
  name: string;
  owner: string;
  total_tracks: number;
  art_url: string | null;
}
