type TrackNodeInfo = {
  recording_mbid: string;
  recording_name: string;
  comment?: string;
  type?: string;
  gender?: string;
  score?: number;
  reference_mbid?: string;
};

type TrackNodeType = {
  id: string;
  recording_mbid: string;
  recording_name: string;
  size: number;
  color: string;
  score: number;
};


type TrackGraphDataType = {
  nodes: Array<TrackNodeType>;
  links: Array<LinkType>;
};
