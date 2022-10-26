import * as React from "react";
import { uniq, includes } from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";
import NamePill from "./NamePill";
import {
  getTrackName,
  getArtistName,
  getRecordingMBID,
  getRecordingMSID,
} from "../utils/utils";
import SearchDropDown from "./SearchDropDown";

export type PersonalRecommendationModalProps = {
  recordingToPersonallyRecommend?: Listen;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
};

export interface PersonalRecommendationModalState {
  blurbContent: string;
  users: Array<string>;
  followers: Array<string>;
  suggestions: Array<string>;
}

export default class PersonalRecommendationModal extends React.Component<
  PersonalRecommendationModalProps,
  PersonalRecommendationModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  readonly maxBlurbContentLength = 280;

  constructor(props: PersonalRecommendationModalProps) {
    super(props);
    this.state = {
      blurbContent: "",
      users: [],
      followers: [],
      suggestions: [],
    };
  }

  componentDidMount(): void {
    const { APIService, currentUser } = this.context;
    APIService.getFollowersOfUser(currentUser.name)
      .then((response) => {
        this.setState({ followers: response.followers });
      })
      .catch((error) => {
        this.handleError(error, "Error while fetching followers");
      });
  }

  handleBlurbInputChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    event.preventDefault();
    const input = event.target.value.replace(/\s\s+/g, " "); // remove line breaks and excessive spaces
    if (input.length <= this.maxBlurbContentLength) {
      this.setState({ blurbContent: input });
    }
  };

  handleError = (error: string | Error, title?: string): void => {
    const { newAlert } = this.props;
    if (!error) {
      return;
    }
    newAlert(
      "danger",
      title || "Error",
      typeof error === "object" ? error.message : error
    );
  };

  addUser = (user: string) => {
    const { users } = this.state;
    this.setState({ users: uniq([...users, user]), suggestions: [] });
  };

  removeUser = (user: string) => {
    const { users } = this.state;
    this.setState({ users: users.filter((element) => element !== user) });
  };

  searchUsers = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { followers } = this.state;
    if (event.target.value) {
      const suggestions = followers.filter((username) =>
        includes(username, event.target.value)
      );
      this.setState({ suggestions });
    } else {
      this.setState({ suggestions: [] });
    }
  };

  closeModal = () => {
    const { APIService, currentUser } = this.context;
    this.setState({
      users: [],
      blurbContent: "",
      suggestions: [],
    });
    // update the followers list
    APIService.getFollowersOfUser(currentUser.name)
      .then((response) => {
        this.setState({ followers: response.followers });
      })
      .catch((error) => {
        this.handleError(error, "Error while fetching followers");
      });
  };

  submitPersonalRecommendation = async () => {
    const { recordingToPersonallyRecommend, newAlert } = this.props;
    const { blurbContent, users } = this.state;
    const { APIService, currentUser } = this.context;

    if (recordingToPersonallyRecommend && currentUser?.auth_token) {
      const metadata: UserTrackPersonalRecommendationMetadata = {
        artist_name: getArtistName(recordingToPersonallyRecommend),
        track_name: getTrackName(recordingToPersonallyRecommend),
        release_name: recordingToPersonallyRecommend!.track_metadata
          .release_name,
        recording_mbid: getRecordingMBID(recordingToPersonallyRecommend),
        recording_msid: getRecordingMSID(recordingToPersonallyRecommend),
        users,
        blurb_content: blurbContent,
      };
      try {
        const status = await APIService.submitPersonalRecommendation(
          currentUser.auth_token,
          currentUser.name,
          metadata
        );
        if (status === 200) {
          newAlert(
            "success",
            `You recommended this track to ${users.length} user${
              users.length > 1 ? "s" : ""
            }`,
            `${metadata.artist_name} - ${metadata.track_name}`
          );
          this.setState({ blurbContent: "" });
        }
      } catch (error) {
        this.handleError(error, "Error while recommending a track");
      }
    }
  };

  render() {
    const { recordingToPersonallyRecommend } = this.props;
    if (!recordingToPersonallyRecommend) {
      return null;
    }
    const { blurbContent, users, suggestions } = this.state;
    const {
      track_name,
      artist_name,
    } = recordingToPersonallyRecommend.track_metadata;
    const { APIService, currentUser } = this.context;
    return (
      <div
        className="modal fade"
        id="PersonalRecommendationModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="PersonalRecommendationModalLabel"
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
              <h4 className="modal-title" id="PersonalRecommendationModalLabel">
                Recommend {track_name} to certain follower(s)
              </h4>
            </div>
            <div className="modal-body">
              {users.map((user) => {
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
                placeholder="Search and add users"
              />
              <SearchDropDown
                suggestions={suggestions}
                // eslint-disable-next-line react/jsx-no-bind
                action={this.addUser}
              />
              <p>
                Tell your above chosen followers why are you recommending them{" "}
                <b>
                  {" "}
                  {track_name} by {artist_name}
                </b>
                <small> (Optional)</small>
              </p>
              <div className="form-group">
                <textarea
                  className="form-control"
                  id="blurb-content"
                  placeholder="Let your followers know why you recommended this song"
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
                The person you want to recommend to isn&apos;t on the drop-down
                list? Do make sure to tell them to follow you by making them go
                to your listen page and clicking the button next to your name!
                And if the name still doesn&apos;t appear then close the modal
                and open it again to see a fresh list of followers!
              </small>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                data-dismiss="modal"
                onClick={this.submitPersonalRecommendation}
              >
                Personally Recommend
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
}
