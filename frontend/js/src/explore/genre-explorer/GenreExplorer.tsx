import * as React from "react";
import { useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { RouteQuery } from "../../utils/Loader";

type GenreExplorerParams = {
  genreMBID: string;
};

type GenreNode = {
  id: string;
  name: string;
};

type GenreExplorerLoaderData = {
  children: GenreNode[];
  parents: {
    nodes: GenreNode[];
    edges: {
      source: string;
      target: string;
    }[];
  };
  siblings: GenreNode[];
  genre: GenreNode;
};

export default function GenreExplorer() {
  const location = useLocation();
  const { genreMBID } = useParams<GenreExplorerParams>();

  const { data } = useQuery<GenreExplorerLoaderData>(
    RouteQuery(["genre-explorer"], location.pathname)
  );
  const { children, parents, siblings, genre } = data || {};

  return <div>Genre Explorer</div>;
}
