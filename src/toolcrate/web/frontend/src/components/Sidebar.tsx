import { NavLink } from "react-router-dom";
import { LayoutDashboard, ListMusic, Briefcase } from "lucide-react";
import { cn } from "@/lib/cn";

const items = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/sources/spotify", label: "Spotify lists", icon: ListMusic },
  { to: "/app/jobs", label: "Jobs", icon: Briefcase },
];

export function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-border bg-card/40">
      <div className="px-4 py-4 text-lg font-semibold tracking-tight">toolcrate</div>
      <nav className="flex flex-col gap-1 px-2">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
