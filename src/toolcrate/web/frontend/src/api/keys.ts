export const queryKeys = {
  lists: { all: ["lists"] as const, byId: (id: number) => ["lists", id] as const },
  tracks: (listId: number, status?: string) => (status ? (["lists", listId, "tracks", { status }] as const) : (["lists", listId, "tracks"] as const)),
  jobs: { all: ["jobs"] as const, list: (filters: Record<string, unknown>) => ["jobs", filters] as const, byId: (id: number) => ["jobs", id] as const },
  preview: (url: string) => ["preview", url] as const,
};
