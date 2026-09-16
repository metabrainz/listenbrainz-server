type GenreExplorerParams = {
  genreName?: string;
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
