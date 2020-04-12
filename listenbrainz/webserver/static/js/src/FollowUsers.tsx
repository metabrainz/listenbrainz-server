import {
  faPlusCircle,
  faSave,
  faSitemap,
  faTimes,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import * as React from "react";
import { isNil as _isNil } from "lodash";
import { getArtistLink, getPlayButton, getTrackLink } from "./utils";

type FollowUsersProps = {
  followList?: Array<string>;
  saveUrl?: string;
  listId?: number;
  listName?: string;
  onUserListChange: (users: Array<string>) => void;
  creator: ListenBrainzUser;
  newAlert: (
    alertType: AlertType,
    title: string,
    message?: string | JSX.Element
  ) => void;
  playingNow: FollowUsersPlayingNow;
  playListen: (listen: Listen) => void;
};

type FollowUsersState = {
  users: Array<string>;
  saveUrl: string;
  listId: number | undefined;
  listName: string | undefined;
};

export default class FollowUsers extends React.Component<
  FollowUsersProps,
  FollowUsersState
> {
  private textInput = React.createRef<HTMLInputElement>();
  private nameInput = React.createRef<HTMLInputElement>();
  constructor(props: FollowUsersProps) {
    super(props);
    this.state = {
      users: props.followList || [],
      saveUrl: props.saveUrl || `${window.location.origin}/1/follow/save`,
      listId: props.listId,
      listName: props.listName,
    };
    this.addUserToList = this.addUserToList.bind(this);
    this.addFollowerOnEnter = this.addFollowerOnEnter.bind(this);
    this.saveListOnEnter = this.saveListOnEnter.bind(this);
  }

  addUserToList = (): void => {
    if (!this.textInput) return;
    if (!this.textInput.current) return;
    const currentValue: string = this.textInput.current.value;
    const { users } = this.state;
    if (
      currentValue === "" ||
      users.find((user: string) => user === currentValue)
    ) {
      return;
    }
    this.setState(
      (prevState: FollowUsersState) => {
        return { users: prevState.users.concat([currentValue]) };
      },
      () => {
        if (this.textInput && this.textInput.current) {
          this.textInput.current.value = "";
        }
        const { onUserListChange } = this.props;
        onUserListChange(users);
      }
    );
  };

  removeUserFromList = (index: number): void => {
    this.setState(
      (prevState: FollowUsersState) => {
        prevState.users.splice(index, 1);
        return { users: prevState.users };
      },
      () => {
        const { onUserListChange } = this.props;
        const { users } = this.state;
        onUserListChange(users);
      }
    );
  };

  saveFollowList = (): void => {
    if (!this.nameInput) return;
    if (!this.nameInput.current) return;

    const { listName, users, listId, saveUrl } = this.state;
    const { creator, newAlert } = this.props;

    let finalListName = listName;
    if (
      !_isNil(this.nameInput.current.value) &&
      this.nameInput.current.value.length
    ) {
      finalListName = this.nameInput.current.value;
    }

    fetch(saveUrl, {
      method: "POST",
      body: JSON.stringify({
        users,
        name: finalListName,
        id: listId,
      }),
      headers: { Authorization: `Token ${creator.auth_token}` },
    })
      .then((response) => {
        if (!response.ok) {
          throw Error(response.statusText);
        }
        newAlert("success", "Successfully saved list");
        return response.json();
      })
      .then((data) => {
        this.setState({ listId: data.list_id });
      })
      .catch((error) => {
        newAlert("danger", "Could not save list", error.message);
      });
  };

  newFollowList = (event: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    event.preventDefault();
    this.setState({
      users: [],
      listId: undefined,
      listName: "",
    });
    if (this.nameInput && this.nameInput.current) {
      this.nameInput.current.value = "";
    }
  };

  addFollowerOnClick = (
    event: React.MouseEvent<HTMLButtonElement, MouseEvent>
  ) => {
    event.preventDefault();
    this.addUserToList();
  };

  saveListOnClick = (
    event: React.MouseEvent<HTMLButtonElement, MouseEvent>
  ) => {
    event.preventDefault();
    this.saveFollowList();
  };

  addFollowerOnEnter(event: React.KeyboardEvent<HTMLInputElement>) {
    event.preventDefault();
    if (event.key === "Enter") {
      this.addUserToList();
    }
  }

  saveListOnEnter(event: React.KeyboardEvent<HTMLInputElement>) {
    event.preventDefault();
    if (event.key === "Enter") {
      this.saveFollowList();
    }
  }

  render() {
    const { listName, users } = this.state;
    const { playingNow, playListen } = this.props;
    const noTopBottomPadding = {
      paddingTop: 0,
      paddingBottom: 0,
    };

    return (
      <div className="panel panel-primary">
        <div className="panel-heading">
          <FontAwesomeIcon icon={faSitemap as IconProp} flip="vertical" />
          <span
            style={{
              fontSize: "x-large",
              marginLeft: "0.55em",
              verticalAlign: "middle",
            }}
          >
            Follow users
          </span>
        </div>
        <div className="panel-body">
          <p className="text-muted">
            Add a user to discover what they are listening to:
          </p>
          <div className="row">
            <div className="col-sm-6">
              <div className="input-group input-group-flex">
                <span className="input-group-addon">Follow user</span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Username…"
                  ref={this.textInput}
                  onKeyPress={this.addFollowerOnEnter}
                />
                <span className="input-group-btn">
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={this.addUserToList}
                  >
                    <FontAwesomeIcon icon={faPlusCircle as IconProp} /> Add
                  </button>
                </span>
              </div>
            </div>
            <div className="col-sm-6">
              <div className="input-group input-group-flex">
                <span className="input-group-addon">Save list</span>
                <input
                  type="text"
                  className="form-control"
                  defaultValue={listName}
                  placeholder="New list name"
                  ref={this.nameInput}
                  onKeyPress={this.saveListOnEnter}
                />
                <div className="input-group-btn">
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={this.saveFollowList.bind(this)}
                  >
                    <FontAwesomeIcon icon={faSave as IconProp} /> Save
                  </button>
                  <button
                    className="btn btn-danger"
                    type="button"
                    onClick={this.newFollowList}
                  >
                    <FontAwesomeIcon icon={faTimes as IconProp} /> Clear
                  </button>
                </div>
              </div>
            </div>
          </div>
          <hr />
          <table className="table table-condensed table-striped listens-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Listening now</th>
                {/* eslint-disable-next-line jsx-a11y/control-has-associated-label */}
                <th style={{ width: "50px" }} />
                {/* eslint-disable-next-line jsx-a11y/control-has-associated-label */}
                <th style={{ width: "65px" }} />
              </tr>
            </thead>
            <tbody>
              {users.map((user, index) => {
                return (
                  <tr
                    key={user}
                    className={playingNow[user] && "playing_now"}
                    onDoubleClick={playListen.bind(this, playingNow[user])}
                  >
                    <td>{user}</td>
                    <td>
                      {playingNow[user] && (
                        <>
                          {getTrackLink(playingNow[user])}
                          <span className="small">
                            {" "}
                            — {getArtistLink(playingNow[user])}
                          </span>
                        </>
                      )}
                    </td>
                    <td className="playButton">
                      {playingNow[user] &&
                        getPlayButton(
                          playingNow[user],
                          playListen.bind(this, playingNow[user])
                        )}
                    </td>
                    <td style={noTopBottomPadding}>
                      <button
                        className="btn btn-danger"
                        type="button"
                        aria-label="Remove"
                        onClick={this.removeUserFromList.bind(this, index)}
                      >
                        <FontAwesomeIcon icon={faTrashAlt as IconProp} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
}
