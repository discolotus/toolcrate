import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useLists } from "@/hooks/useLists";
import { ListMasterTable } from "@/components/ListMasterTable";
import { AddListDialog } from "@/components/AddListDialog";

export default function SpotifyLists() {
  const { id } = useParams();
  const selectedId = id ? Number(id) : undefined;
  const navigate = useNavigate();
  const lists = useLists({ source_type: "spotify_playlist" });
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Spotify lists</h1>
        <Button onClick={() => setOpen(true)}>Add Spotify list</Button>
      </div>
      <ListMasterTable items={lists.data?.items ?? []} selectedId={selectedId} />
      {open && (
        <AddListDialog
          open
          onClose={(created) => {
            setOpen(false);
            if (created) navigate(`/app/lists/${created.id}`);
          }}
        />
      )}
    </div>
  );
}
