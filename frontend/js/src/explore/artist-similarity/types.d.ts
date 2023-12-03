type ArtistType = {
  artist_mbid: string;
  name: string;
  comment?: string;
  type?: string;
  gender?: string;
  score?: number;
  reference_mbid?: string;
};

type MarkupResponseType = {
  data: string;
  type: "markup";
};

type DatasetResponseType = {
  columns: Array<string>;
  data: Array<ArtistType>;
  type: "dataset";
};

type ApiResponseType = Array<MarkupResponseType | DatasetResponseType>;

type NodeType = {
  id: string;
  artist_mbid: string;
  artist_name: string;
  size: number;
  color: string;
  score: number;
};

type LinkType = {
  source: string;
  target: string;
  distance: number;
};

type GraphDataType = {
  nodes: Array<NodeType>;
  links: Array<LinkType>;
};
