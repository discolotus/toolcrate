import { describe, it, expect, vi, beforeEach } from "vitest";
import { dispatchSseEvent, type SseEvent } from "@/api/sse";

const invalidate = vi.fn();
const queryClient = { invalidateQueries: invalidate } as unknown as import("@tanstack/react-query").QueryClient;

beforeEach(() => invalidate.mockReset());

function ev(name: string, data: unknown): SseEvent {
  return { name, data };
}

describe("dispatchSseEvent", () => {
  it("invalidates lists on list.created", () => {
    dispatchSseEvent(queryClient, ev("list.created", { id: 1 }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists"] });
  });

  it("invalidates lists + specific list on list.updated", () => {
    dispatchSseEvent(queryClient, ev("list.updated", { id: 7 }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists", 7] });
  });

  it("invalidates jobs and source list on job.update with source_list_id", () => {
    dispatchSseEvent(queryClient, ev("job.update", { id: 9, source_list_id: 42 }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["jobs"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists", 42] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists", 42, "tracks"] });
  });

  it("invalidates tracks on track.updated", () => {
    dispatchSseEvent(queryClient, ev("track.updated", { source_list_id: 3 }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["lists", 3, "tracks"] });
  });

  it("ignores unknown event types", () => {
    dispatchSseEvent(queryClient, ev("mystery.thing", {}));
    expect(invalidate).not.toHaveBeenCalled();
  });
});
