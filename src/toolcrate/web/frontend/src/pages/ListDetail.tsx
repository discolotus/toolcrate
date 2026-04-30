import { useParams } from "react-router-dom";

export default function ListDetail() {
  const { id } = useParams();
  return <h1 className="text-2xl font-semibold">List {id}</h1>;
}
