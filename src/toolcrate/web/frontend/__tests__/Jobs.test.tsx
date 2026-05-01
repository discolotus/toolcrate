import { describe, it, expect } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Jobs from "@/pages/Jobs";
import { server, http, HttpResponse } from "@/test/msw-handlers";

function wrap(ui: React.ReactNode, initialEntries = ["/app/jobs"]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

const job = (over: Partial<Record<string, unknown>> = {}) => ({
  id: 1,
  type: "sync_list",
  state: "running",
  priority: 0,
  source_list_id: 1,
  attempts: 1,
  max_attempts: 3,
  scheduled_for: "2026-04-30T00:00:00Z",
  started_at: "2026-04-30T00:00:00Z",
  finished_at: null,
  progress_json: { current: 5, total: 20 },
  error: null,
  ...over,
});

describe("Jobs page", () => {
  it("renders jobs from server", async () => {
    server.use(http.get("/api/v1/jobs", () => HttpResponse.json({ items: [job()], total: 1, limit: 100, offset: 0 })));
    render(wrap(<Jobs />));
    expect(await screen.findByText(/5 \/ 20/)).toBeInTheDocument();
  });

  it("shows Cancel only on running jobs", async () => {
    server.use(
      http.get("/api/v1/jobs", () =>
        HttpResponse.json({
          items: [job({ id: 1, state: "running" }), job({ id: 2, state: "success" })],
          total: 2,
          limit: 100,
          offset: 0,
        }),
      ),
    );
    render(wrap(<Jobs />));
    await screen.findByText(/sync_list/);
    const cancels = screen.getAllByRole("button", { name: /cancel/i });
    expect(cancels).toHaveLength(1);
  });

  it("filters by state via the state buttons", async () => {
    let lastUrl = "";
    server.use(
      http.get("/api/v1/jobs", ({ request }) => {
        lastUrl = request.url;
        return HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 });
      }),
    );
    render(wrap(<Jobs />));
    await waitFor(() => expect(lastUrl).toContain("/jobs"));
    await userEvent.click(screen.getByRole("button", { name: /^running$/i }));
    await waitFor(() => expect(lastUrl).toContain("state=running"));
  });
});
