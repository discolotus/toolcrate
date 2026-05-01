import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { useEffect, useState } from "react";
import { router } from "./router";

export default function App() {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 5_000, refetchOnWindowFocus: false },
        },
      }),
  );
  const [ready, setReady] = useState(false);

  useEffect(() => {
    fetch("/api/v1/auth/bootstrap", { credentials: "include" }).finally(() =>
      setReady(true),
    );
  }, []);

  if (!ready) return null;

  return (
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
