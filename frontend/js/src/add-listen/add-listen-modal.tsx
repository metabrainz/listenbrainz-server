import * as React from "react";
import GlobalAppContext from "../utils/GlobalAppContext";
import SearchDropDown from "./SearchDropDown";

type TrackType = {
  artist_credit_id: number;
  artist_credit_name: string;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
};

export interface AddListenModalState {
  ListenOption: string;
  SearchField: string;
  TrackResults: Array<TrackType>;
  SelectedTrack: TrackType;
}

export default class AddListenModal extends React.Component<
  AddListenModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props) {
    super(props);
    this.state = {
      ListenOption: "track",
      SearchField: "",
      TrackResults: [],
      SelectedTrack: {},
    };
  }

  closeModal = () => {};

  addTrack = () => {
    this.setState({
      ListenOption: "track",
    });
  };

  addAlbum = () => {
    this.setState({
      ListenOption: "album",
    });
  };

  TrackName = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { SearchField } = this.state;
    this.setState({
      SearchField: event.target.value,
    });
  };

  SearchTrack = async () => {
    const { SearchField } = this.state;
    try {
      const response = await fetch(
        "https://labs.api.listenbrainz.org/recording-search/json",
        {
          method: "POST",
          body: JSON.stringify([{ query: SearchField }]),
          headers: {
            "Content-type": "application/json; charset=UTF-8",
          },
        }
      );

      const parsedResponse = await response.json();
      this.setState(
        {
          TrackResults: parsedResponse,
        },
        () => {
          console.log(this.state.TrackResults);
        }
      );
    } catch (error) {
      console.debug(error);
    }
  };

  addTrackMetadata = (track: TrackType) => {
    this.setState(
      {
        SelectedTrack: track,
      },
      () => {
        console.log(this.state.SelectedTrack);
      }
    );
  };

  componentDidUpdate(pp, ps, ss) {
    if (ps.SearchField !== this.state.SearchField) {
      this.SearchTrack();
    }
  }

  render() {
    const { ListenOption, TrackResults } = this.state;
    return (
      <div
        className="modal fade"
        id="AddListenModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="AddListenModalLabel"
        data-backdrop="static"
      >
        <div className="modal-dialog" role="document">
          <form className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                data-dismiss="modal"
                aria-label="Close"
                onClick={this.closeModal}
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="AddListenModalLabel">
                Add Listens
              </h4>
            </div>
            <div className="modal-body">
              <div className="add-listen-header">
                <button
                  type="button"
                  className={`btn btn-primary add-listen ${
                    ListenOption == "track"
                      ? "option-active"
                      : "option-unactive"
                  }`}
                  onClick={this.addTrack}
                >
                  Add track
                </button>
                <button
                  type="button"
                  className={`btn btn-primary add-listen ${
                    ListenOption == "album"
                      ? "option-active"
                      : "option-unactive"
                  }`}
                  onClick={this.addAlbum}
                >
                  Add album
                </button>
              </div>
              <input
                type="text"
                className="form-control add-track-field"
                onChange={this.TrackName}
                placeholder="Add Artist name followed by Track name"
              />
              <SearchDropDown
                TrackResults={TrackResults}
                action={this.addTrackMetadata}
              />
              {/* {users.map((user) => {
                return (
                  <NamePill
                    title={user}
                    // eslint-disable-next-line react/jsx-no-bind
                    closeAction={this.removeUser.bind(this, user)}
                  />
                );
              })}
              <input
                type="text"
                className="form-control"
                onChange={this.searchUsers}
                placeholder="Add followers*"
              />
              <SearchDropDown
                suggestions={suggestions}
                // eslint-disable-next-line react/jsx-no-bind
                action={this.addUser}
              />
              <p>Leave a message (optional)</p>
              <div className="form-group">
                <textarea
                  className="form-control"
                  id="blurb-content"
                  placeholder="You will love this song because..."
                  value={blurbContent}
                  name="blurb-content"
                  rows={4}
                  style={{ resize: "vertical" }}
                  onChange={this.handleBlurbInputChange}
                />
              </div>
              <small className="character-count">
                {blurbContent.length} / {this.maxBlurbContentLength}
                <br />
                *Can’t find a user? Make sure they are following you, and then
                try again.
              </small> */}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
              >
                Cancel
              </button>
              {/* <button
                type="submit"
                className="btn btn-success"
                data-dismiss="modal"
                disabled={users.length === 0}
                onClick={this.submitPersonalRecommendation}
              >
                Send Recommendation
              </button> */}
            </div>
          </form>
        </div>
      </div>
    );
  }
}
