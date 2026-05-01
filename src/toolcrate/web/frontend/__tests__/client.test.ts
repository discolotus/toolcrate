import { describe, it, expect } from "vitest";
import { ApiError, apiFetch } from "@/api/client";
import { server, http, HttpResponse } from "@/test/msw-handlers";

describe("apiFetch", () => {
  it("returns parsed JSON on 2xx", async () => {
    server.use(
      http.get("/api/v1/lists", () => HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 })),
    );
    const data = await apiFetch<{ total: number }>("/api/v1/lists");
    expect(data.total).toBe(0);
  });

  it("returns null on 204", async () => {
    server.use(http.delete("/api/v1/lists/1", () => new HttpResponse(null, { status: 204 })));
    const data = await apiFetch<null>("/api/v1/lists/1", { method: "DELETE" });
    expect(data).toBeNull();
  });

  it("throws ApiError with parsed RFC 7807 body", async () => {
    server.use(
      http.post("/api/v1/lists/preview", () =>
        HttpResponse.json(
          { type: "about:blank#bad_url", title: "Bad URL", status: 400, detail: "unsupported source url", code: "bad_url" },
          { status: 400, headers: { "content-type": "application/problem+json" } },
        ),
      ),
    );
    await expect(
      apiFetch("/api/v1/lists/preview", { method: "POST", body: JSON.stringify({}) }),
    ).rejects.toMatchObject({ status: 400, code: "bad_url", title: "Bad URL" });
  });

  it("throws generic ApiError on non-JSON 5xx", async () => {
    server.use(http.get("/api/v1/jobs", () => new HttpResponse("oops", { status: 500 })));
    let caught: unknown;
    try {
      await apiFetch("/api/v1/jobs");
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(500);
  });

  it("sends credentials and JSON content-type by default", async () => {
    let capturedRequest: Request | undefined;
    server.use(
      http.post("/api/v1/lists", async ({ request }) => {
        capturedRequest = request;
        return HttpResponse.json({ id: 1 }, { status: 201 });
      }),
    );
    await apiFetch("/api/v1/lists", { method: "POST", body: JSON.stringify({ name: "x" }) });
    expect(capturedRequest?.headers.get("content-type")).toBe("application/json");
    expect(capturedRequest?.credentials).toBe("include");
  });
});
