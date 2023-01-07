import * as React from "react";
import GlobalAppContext from "../utils/GlobalAppContext";

type TrackType = {
  artist_credit_id: number;
  artist_credit_name: string;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
};

export type SearchDropDownState = {};

export type SearchDropDownProps = {
  TrackResults?: Array<TrackType>;
  action: (event: TrackType) => void;
};

export default class SearchDropDown extends React.Component<
  SearchDropDownProps,
  SearchDropDownState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  render() {
    const { TrackResults, action } = this.props;
    return (
      <div className="tracksearchdropdown">
        {TrackResults?.map((track) => {
          return (
            <button
              type="button"
              onClick={() => {
                action(track);
              }}
            >
              {`${track.recording_name} - ${track.artist_credit_name}`}
            </button>
          );
        })}
      </div>
    );
  }
}
