import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { server, http, HttpResponse } from "@/test/msw-handlers";
import { AddListDialog } from "@/components/AddListDialog";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("AddListDialog", () => {
  it("autofills name from preview after URL paste", async () => {
    server.use(
      http.post("/api/v1/lists/preview", () =>
        HttpResponse.json({
          source_type: "spotify_playlist",
          external_id: "abc",
          name: "Beach Vibes",
          owner: "spotify",
          total_tracks: 12,
          art_url: null,
        }),
      ),
    );
    render(wrap(<AddListDialog open onClose={vi.fn()} />));

    const url = await screen.findByLabelText(/playlist url/i);
    await userEvent.type(url, "https://open.spotify.com/playlist/abc");

    const name = await screen.findByLabelText(/name/i);
    await waitFor(() => expect(name).toHaveValue("Beach Vibes"));
    expect(screen.getByText(/12 tracks/i)).toBeInTheDocument();
  });

  it("shows error when preview returns 400", async () => {
    server.use(
      http.post("/api/v1/lists/preview", () =>
        HttpResponse.json(
          { type: "about:blank#bad_url", title: "Bad URL", status: 400, detail: "unsupported", code: "bad_url" },
          { status: 400, headers: { "content-type": "application/problem+json" } },
        ),
      ),
    );
    render(wrap(<AddListDialog open onClose={vi.fn()} />));
    await userEvent.type(await screen.findByLabelText(/playlist url/i), "https://open.spotify.com/playlist/badid");
    expect(await screen.findByText(/unsupported|bad url/i)).toBeInTheDocument();
  });

  it("submits and calls onClose on success", async () => {
    let captured: Request | undefined;
    server.use(
      http.post("/api/v1/lists/preview", () =>
        HttpResponse.json({
          source_type: "spotify_playlist",
          external_id: "abc",
          name: "Beach Vibes",
          owner: "spotify",
          total_tracks: 12,
          art_url: null,
        }),
      ),
      http.post("/api/v1/lists", async ({ request }) => {
        captured = request.clone();
        return HttpResponse.json({ id: 7 }, { status: 201 });
      }),
    );
    const onClose = vi.fn();
    render(wrap(<AddListDialog open onClose={onClose} />));

    await userEvent.type(await screen.findByLabelText(/playlist url/i), "https://open.spotify.com/playlist/abc");
    await waitFor(() => expect(screen.getByLabelText(/name/i)).toHaveValue("Beach Vibes"));
    await userEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => expect(onClose).toHaveBeenCalledWith({ id: 7 }));
    const body = captured ? await captured.json() : {};
    expect(body).toMatchObject({
      name: "Beach Vibes",
      source_url: "https://open.spotify.com/playlist/abc",
      source_type: "spotify_playlist",
    });
  });
});
