import * as React from "react";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import { uniq, includes, remove } from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";
import ListenControl from "../listens/ListenControl";
import Pill from "./Pill";
import {
  getTrackName,
  getArtistName,
  getRecordingMBID,
  getRecordingMSID,
} from "../utils/utils";

export type PersonalRecommendationModalProps = {
  recordingToPersonallyRecommend?: Listen;
  newAlert: (
    alertType: AlertType,
    title: string,
    message: string | JSX.Element
  ) => void;
  onSuccessfulPersonalRecommendation?: UserTrackPersonalRecommendationMetadata;
};

export interface PersonalRecommendationModalState {
  blurbContent: string;
  users: Array<string> | null;
  followers: Array<string> | null;
  suggestions: Array<string> | null;
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
    users!.push(user);
    this.setState({ users: uniq(users), suggestions: [] });
  };

  removeUser = (user: string) => {
    const { users } = this.state;
    remove(users!, (element) => {
      return element === user;
    });
    this.setState({ users });
  };

  searchUsers = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { followers } = this.state;
    if (event.target.value) {
      const suggestions = followers!.filter((username) => {
        if (includes(username, event.target.value)) {
          return username;
        }
        return null;
      });
      this.setState({ suggestions });
    } else {
      this.setState({ suggestions: [] });
    }
  };

  submitPersonalRecommendation = async () => {
    const { recordingToPersonallyRecommend, newAlert } = this.props;
    const { blurbContent, users } = this.state;
    const { APIService, currentUser } = this.context;

    if (currentUser?.auth_token) {
      const metadata: UserTrackPersonalRecommendationMetadata = {
        artist_name: getArtistName(recordingToPersonallyRecommend),
        track_name: getTrackName(recordingToPersonallyRecommend),
        release_name: recordingToPersonallyRecommend!.track_metadata
          .release_name,
        recording_mbid: getRecordingMBID(recordingToPersonallyRecommend!),
        recording_msid: getRecordingMSID(recordingToPersonallyRecommend!),
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
            "You personally recommended a track!",
            `${metadata.artist_name} - ${metadata.track_name}`
          );
        }
      } catch (error) {
        this.handleError(error, "Error while personally recommending");
      }
    }
  };

  render() {
    const { recordingToPersonallyRecommend } = this.props;
    if (!recordingToPersonallyRecommend) {
      return null;
    }
    const { blurbContent, users, suggestions } = this.state;
    const { track_name } = recordingToPersonallyRecommend.track_metadata;
    const { artist_name } = recordingToPersonallyRecommend.track_metadata;
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
                onClick={() => {
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
                }}
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="PersonalRecommendationModalLabel">
                Personally recommend this recording
              </h4>
            </div>
            <div className="modal-body">
              {users!.map((user) => {
                return (
                  <Pill
                    title={user}
                    // eslint-disable-next-line react/jsx-no-bind
                    closeAction={this.removeUser.bind(this, user)}
                    closeButton
                  />
                );
              })}
              <input
                type="text"
                className="form-control"
                onChange={this.searchUsers}
                placeholder="Search and add users"
              />
              <div className="searchdropdown">
                {suggestions!.map((name) => {
                  return (
                    <ListenControl
                      text={name}
                      // eslint-disable-next-line react/jsx-no-bind
                      action={this.addUser.bind(this, name)}
                      icon={faUser}
                    />
                  );
                })}
              </div>
              <p style={{ marginTop: "10px" }}>
                Why will you recommend personally{" "}
                <b>
                  {" "}
                  {track_name} by {artist_name}
                </b>
                ? (Optional)
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
                  spellCheck="false"
                  onChange={this.handleBlurbInputChange}
                />
              </div>
              <small style={{ display: "block", textAlign: "right" }}>
                {blurbContent.length} / {this.maxBlurbContentLength}
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
