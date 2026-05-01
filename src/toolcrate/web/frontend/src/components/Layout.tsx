import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { LiveBadge } from "./LiveBadge";
import { useSseInvalidation } from "@/hooks/useSseInvalidation";
import { Toaster } from "sonner";

export function Layout() {
  const { live } = useSseInvalidation();
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center justify-end border-b border-border px-4">
          <LiveBadge live={live} />
        </header>
        <main className="min-w-0 flex-1 p-6">
          <Outlet />
        </main>
      </div>
      <Toaster richColors position="top-right" />
    </div>
  );
}
