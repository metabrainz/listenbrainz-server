import * as React from "react";
import { getPlaylistExtension, getPlaylistId } from "./utils";
import GlobalAppContext from "../utils/GlobalAppContext";
import UserSearch from "./UserSearch";
import NamePill from "../personal-recommendations/NamePill";
import { WithAlertNotificationsInjectedProps } from "../notifications/AlertNotificationsHOC";

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
} & WithAlertNotificationsInjectedProps;

type CreateOrEditPlaylistModalState = {
  name: string;
  description: string;
  isPublic: boolean;
  collaborators: string[];
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
    };
  }

  // We make the component reusable by updating the state
  // when props change (when we pass another playlist)
  componentDidUpdate(prevProps: CreateOrEditPlaylistModalProps) {
    const { playlist } = this.props;

    if (getPlaylistId(prevProps.playlist) !== getPlaylistId(playlist)) {
      const customFields = getPlaylistExtension(playlist);
      this.setState({
        name: playlist?.title ?? "",
        description: playlist?.annotation ?? "",
        isPublic: customFields?.public ?? true,
        collaborators: customFields?.collaborators ?? [],
      });
    }
  }

  clear = () => {
    this.setState({
      name: "",
      description: "",
      isPublic: true,
      collaborators: [],
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

  addCollaborator = (user: string): void => {
    const { playlist } = this.props;
    const isEdit = Boolean(getPlaylistId(playlist));
    const { collaborators } = this.state;
    const { currentUser } = this.context;
    const disabled =
      !user ||
      (isEdit
        ? playlist?.creator.toLowerCase() === user.toLowerCase()
        : currentUser.name.toLowerCase() === user.toLowerCase());
    if (!disabled && collaborators.indexOf(user) === -1) {
      this.setState({
        collaborators: [...collaborators, user],
      });
    }
  };

  render() {
    const { name, description, isPublic, collaborators } = this.state;
    const { htmlId, playlist, newAlert } = this.props;
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
                  {/* eslint-disable-next-line jsx-a11y/label-has-associated-control */}
                  <label style={{ display: "block" }}>Collaborators</label>

                  {collaborators.map((user) => {
                    return (
                      <NamePill
                        title={user}
                        // eslint-disable-next-line react/jsx-no-bind
                        closeAction={this.removeCollaborator.bind(this, user)}
                      />
                    );
                  })}
                </div>

                <UserSearch
                  onSelectUser={this.addCollaborator}
                  placeholder="Add collaborator"
                  newAlert={newAlert}
                />
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
