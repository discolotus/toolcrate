import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TrackTable } from "@/components/TrackTable";
import type { TrackEntry } from "@/api/resources";

const t = (over: Partial<TrackEntry> = {}): TrackEntry => ({
  id: 1,
  source_list_id: 1,
  position: 1,
  artist: "A",
  title: "T",
  album: "Alb",
  duration_sec: 200,
  isrc: null,
  spotify_track_id: null,
  download_status: "pending",
  first_seen_at: "2026-04-30T00:00:00Z",
  last_seen_at: "2026-04-30T00:00:00Z",
  ...over,
});

describe("TrackTable", () => {
  it("renders rows with status pill", () => {
    render(<TrackTable items={[t({ id: 1, title: "Song A", download_status: "done" }), t({ id: 2, title: "Song B", download_status: "failed" })]} onRetry={vi.fn()} />);
    expect(screen.getByText("Song A")).toBeInTheDocument();
    expect(screen.getByText("Song B")).toBeInTheDocument();
    expect(screen.getByText("done")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("calls onRetry when retry clicked on failed row", async () => {
    const onRetry = vi.fn();
    render(<TrackTable items={[t({ id: 99, download_status: "failed" })]} onRetry={onRetry} />);
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledWith(99);
  });

  it("does not show retry button on done rows", () => {
    render(<TrackTable items={[t({ id: 1, download_status: "done" })]} onRetry={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("renders empty state when no items", () => {
    render(<TrackTable items={[]} onRetry={vi.fn()} />);
    expect(screen.getByText(/no tracks yet/i)).toBeInTheDocument();
  });
});
