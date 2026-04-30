import { createBrowserRouter, Navigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import SpotifyLists from "@/pages/SpotifyLists";
import ListDetail from "@/pages/ListDetail";
import Jobs from "@/pages/Jobs";

export const router = createBrowserRouter([
  {
    path: "/app",
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "sources/spotify", element: <SpotifyLists /> },
      { path: "lists/:id", element: <ListDetail /> },
      { path: "jobs", element: <Jobs /> },
      { path: "*", element: <Navigate to="/app" replace /> },
    ],
  },
  { path: "/", element: <Navigate to="/app" replace /> },
  { path: "*", element: <Navigate to="/app" replace /> },
]);
