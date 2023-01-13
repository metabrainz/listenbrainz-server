import * as React from "react";
import { getPlaylistExtension, getPlaylistId } from "./utils";
import GlobalAppContext from "../utils/GlobalAppContext";
import SearchDropDown from "./SearchDropDown";
import Pill from "./Pill";

type CreateOrEditPlaylistModalProps = {
  playlist?: JSPFPlaylist;
  onSubmit: (
    title: string,
    description: string,
    isPublic: boolean,
    collaborators: string[],
    id?: string,
    onSuccessCallback?: () => void
  ) => void;
  htmlId?: string;
};

type CreateOrEditPlaylistModalState = {
  name: string;
  description: string;
  isPublic: boolean;
  collaborators: string[];
  newCollaborator: string;
  userSearchResults: Array<string>;
};

export default class CreateOrEditPlaylistModal extends React.Component<
  CreateOrEditPlaylistModalProps,
  CreateOrEditPlaylistModalState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: CreateOrEditPlaylistModalProps) {
    super(props);
    const customFields = getPlaylistExtension(props.playlist);
    this.state = {
      name: props.playlist?.title ?? "",
      description: props.playlist?.annotation ?? "",
      isPublic: customFields?.public ?? true,
      collaborators: customFields?.collaborators ?? [],
      newCollaborator: "",
      userSearchResults: [],
    };
  }

  // We make the component reusable by updating the state
  // when props change (when we pass another playlist)
  componentDidUpdate(
    prevProps: CreateOrEditPlaylistModalProps,
    prevState: CreateOrEditPlaylistModalState
  ) {
    const { playlist } = this.props;

    if (getPlaylistId(prevProps.playlist) !== getPlaylistId(playlist)) {
      const customFields = getPlaylistExtension(playlist);
      this.setState({
        name: playlist?.title ?? "",
        description: playlist?.annotation ?? "",
        isPublic: customFields?.public ?? true,
        collaborators: customFields?.collaborators ?? [],
        newCollaborator: "",
      });
    }

    const {newCollaborator} = this.state;

    if (prevState.newCollaborator !== newCollaborator) {
      this.searchUsers();
    }
  }

  clear = () => {
    this.setState({
      name: "",
      description: "",
      isPublic: true,
      collaborators: [],
      newCollaborator: "",
      userSearchResults: [],
    });
  };

  submit = (event: React.SyntheticEvent) => {
    event.preventDefault();
    const { onSubmit, playlist } = this.props;
    const { name, description, isPublic, collaborators } = this.state;

    // VALIDATION PLEASE !
    onSubmit(
      name,
      description,
      isPublic,
      collaborators,
      getPlaylistId(playlist),
      this.clear.bind(this)
    );
  };

  handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { target } = event;
    const value =
      target.type === "checkbox"
        ? (target as HTMLInputElement).checked
        : target.value;
    const { name } = target;
    // @ts-ignore
    this.setState({
      [name]: value,
    });
  };

  removeCollaborator = (username: string): void => {
    const { collaborators } = this.state;
    this.setState({
      collaborators: collaborators.filter(
        (collabName) => collabName !== username
      ),
    });
  };

  addCollaborator = (collaborator: string): void => {
    const { collaborators, newCollaborator } = this.state;
    if (collaborators.indexOf(collaborator) !== -1) {
      // already in the list
      this.setState({ newCollaborator: "" });
      return;
    }
    this.setState({
      collaborators: [...collaborators, collaborator],
      newCollaborator: "",
    });
  };

  searchUsers = async () => {
    const { currentUser } = this.context;
    const { newCollaborator } = this.state;
    if (currentUser?.auth_token) {
      try {
        const url = new URL("http://localhost:8100/1/playlist/search/users/");
        url.searchParams.append("search_term", newCollaborator);
        const response = await fetch(url.toString(), {
          method: "GET",
          headers: {
            Authorization: `Token ${currentUser.auth_token}`,
            "Content-Type": "application/json;charset=UTF-8",
          },
        });
        const results: Array<string> = [];
        const parsedResponse = await response.json();
        parsedResponse.users.map((user: any) => {
          results.push(user[0]);
          return;
        });
        this.setState({
          userSearchResults: results,
        });

      } catch (error) {
        console.debug(error);
      }
    }
  };

  render() {
    const {
      name,
      description,
      isPublic,
      collaborators,
      newCollaborator,
      userSearchResults,
    } = this.state;
    const { htmlId, playlist } = this.props;
    const { currentUser } = this.context;
    const isEdit = Boolean(getPlaylistId(playlist));
    return (
      <div
        className="modal fade"
        id={htmlId ?? "playlistModal"}
        tabIndex={-1}
        role="dialog"
        aria-labelledby="playlistModalLabel"
      >
        <div className="modal-dialog" role="document">
          <form className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                data-dismiss="modal"
                aria-label="Close"
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="playlistModalLabel">
                {isEdit ? "Edit" : "Create"} playlist
              </h4>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label htmlFor="playlistName">Name</label>
                <input
                  type="text"
                  className="form-control"
                  id="playlistName"
                  placeholder="Name"
                  value={name}
                  name="name"
                  onChange={this.handleInputChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="playlistdescription">Description</label>
                <textarea
                  className="form-control"
                  id="playlistdescription"
                  placeholder="Description"
                  value={description}
                  name="description"
                  onChange={this.handleInputChange}
                />
              </div>
              <div className="checkbox">
                <label>
                  <input
                    id="isPublic"
                    type="checkbox"
                    checked={isPublic}
                    name="isPublic"
                    onChange={this.handleInputChange}
                  />
                  &nbsp;Make playlist public
                </label>
              </div>

              <div className="form-group">
                <div>
                  <label
                    htmlFor="playlistcollaborators"
                    style={{ display: "block" }}
                  >
                    Collaborators
                  </label>

                  {collaborators.map((user) => {
                    return (
                      <Pill
                        collaboratorName={user}
                        removeCollaborator={this.removeCollaborator}
                      />
                    );
                  })}
                </div>

                <div>
                  <input
                    type="text"
                    className="form-control"
                    onChange={this.handleInputChange}
                    placeholder="Add collaborator"
                    value={newCollaborator}
                    name="newCollaborator"
                  />
                  <SearchDropDown
                    addCollaborator={this.addCollaborator}
                    userSearchResults={userSearchResults}
                  />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
                onClick={this.clear}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                onClick={this.submit}
                data-dismiss="modal"
              >
                {isEdit ? "Save" : "Create"}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
}
