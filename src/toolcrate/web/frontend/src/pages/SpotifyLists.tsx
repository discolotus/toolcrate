import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useLists } from "@/hooks/useLists";
import { ListMasterTable } from "@/components/ListMasterTable";
import { ListDetailPanel } from "@/components/ListDetailPanel";
import { AddListDialog } from "@/components/AddListDialog";

export default function SpotifyLists() {
  const { id } = useParams();
  const selectedId = id ? Number(id) : undefined;
  const navigate = useNavigate();
  const lists = useLists({ source_type: "spotify_playlist" });
  const [open, setOpen] = useState(false);

  return (
    <div className="flex -m-6 min-h-[calc(100vh-3rem)]">
      {/* Left: master table */}
      <div className="flex w-72 shrink-0 flex-col border-r border-border">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h1 className="text-lg font-semibold">Spotify lists</h1>
          <Button size="sm" onClick={() => setOpen(true)}>
            Add
          </Button>
        </div>
        <div className="flex-1 overflow-auto">
          <ListMasterTable
            items={lists.data?.items ?? []}
            selectedId={selectedId}
            onSelect={(listId) => navigate(`/app/sources/spotify/${listId}`)}
          />
        </div>
      </div>

      {/* Right: detail panel or empty state */}
      <div className="flex-1 overflow-auto p-6">
        {selectedId != null ? (
          <ListDetailPanel listId={selectedId} />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Select a list to view details
          </div>
        )}
      </div>

      {open && (
        <AddListDialog
          open
          onClose={(created) => {
            setOpen(false);
            if (created) navigate(`/app/sources/spotify/${created.id}`);
          }}
        />
      )}
    </div>
  );
}
