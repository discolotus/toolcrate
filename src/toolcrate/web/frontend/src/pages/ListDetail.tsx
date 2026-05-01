import { useParams, Navigate } from "react-router-dom";
import { ListDetailPanel } from "@/components/ListDetailPanel";

export default function ListDetail() {
  const { id } = useParams();
  const numericId = id ? Number(id) : NaN;
  if (!Number.isFinite(numericId)) return <Navigate to="/app/sources/spotify" replace />;
  return <ListDetailPanel listId={numericId} />;
}
