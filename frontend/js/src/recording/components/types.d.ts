type RecordingNodeInfo = {
  recording_mbid: string;
  recording_name: string;
  comment?: string;
  type?: string;
  gender?: string;
  score?: number;
  reference_mbid?: string;
};

type RecordingNodeType = {
  id: string;
  recording_mbid: string;
  recording_name: string;
  size: number;
  color: string;
  score: number;
};


type RecordingGraphDataType = {
  nodes: Array<RecordingNodeType>;
  links: Array<LinkType>;
};
