import * as React from "react";
import {
  faPlusCircle,
  faTimes,
  faTrashAlt,
} from "@fortawesome/free-solid-svg-icons";

import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

type CreateOrEditPlaylistModalProps = {
  playlist?: ListenBrainzPlaylist;
  onSubmit: (
    name: string,
    description: string,
    isPublic: boolean,
    collaborators: string[],
    id?: string
  ) => void;
  htmlId?: string;
};

type CreateOrEditPlaylistModalState = {
  name: string;
  description: string;
  isPublic: boolean;
  collaborators: string[];
  newCollaborator: string;
};

export default class CreateOrEditPlaylistModal extends React.Component<
  CreateOrEditPlaylistModalProps,
  CreateOrEditPlaylistModalState
> {
  constructor(props: CreateOrEditPlaylistModalProps) {
    super(props);

    this.state = {
      name: props.playlist?.title ?? "",
      description: props.playlist?.annotation ?? "",
      isPublic: props.playlist?.public ?? true,
      collaborators: props.playlist?.collaborators ?? [],
      newCollaborator: "",
    };
  }

  // We make the component reusable by updating the state
  // when props change (when we pass another playlist)
  componentDidUpdate(prevProps: CreateOrEditPlaylistModalProps) {
    const { playlist } = this.props;
    if (prevProps.playlist?.id !== playlist?.id) {
      this.setState({
        name: playlist?.title ?? "",
        description: playlist?.annotation ?? "",
        isPublic: playlist?.public ?? true,
        collaborators: playlist?.collaborators ?? [],
        newCollaborator: "",
      });
    }
  }

  submit = (event: React.SyntheticEvent) => {
    event.preventDefault();
    const { onSubmit, playlist } = this.props;
    const { name, description, isPublic, collaborators } = this.state;

    // VALIDATION PLEASE !
    onSubmit(name, description, isPublic, collaborators, playlist?.id);
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

  addCollaborator = (evt: React.FormEvent<HTMLFormElement>): void => {
    evt.preventDefault();
    const { collaborators, newCollaborator } = this.state;
    if (collaborators.indexOf(newCollaborator) !== -1) {
      // already in the list
      this.setState({ newCollaborator: "" });
      return;
    }
    this.setState({
      collaborators: [...collaborators, newCollaborator],
      newCollaborator: "",
    });
  };

  render() {
    const {
      name,
      description,
      isPublic,
      collaborators,
      newCollaborator,
    } = this.state;
    const { htmlId, playlist } = this.props;

    const isEdit = Boolean(playlist?.id);
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
                <label htmlFor="playlistcollaborators">Collaborators</label>
                <table
                  id="playlistcollaborators"
                  className="table table-condensed table-striped listens-table"
                >
                  <tbody>
                    {collaborators.map((user, index) => {
                      return (
                        <tr key={user}>
                          <td>{user}</td>

                          <td
                            style={{
                              paddingTop: 0,
                              paddingBottom: 0,
                              width: "30px",
                            }}
                          >
                            <button
                              className="btn btn-link"
                              type="button"
                              aria-label="Remove"
                              onClick={this.removeCollaborator.bind(this, user)}
                            >
                              <FontAwesomeIcon icon={faTimes as IconProp} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <form
                  className="input-group input-group-flex"
                  onSubmit={this.addCollaborator}
                >
                  <span className="input-group-addon">Add collaborator</span>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Username…"
                    name="newCollaborator"
                    onChange={this.handleInputChange}
                    value={newCollaborator}
                  />
                  <span className="input-group-btn">
                    <button className="btn" type="submit">
                      <FontAwesomeIcon icon={faPlusCircle as IconProp} /> Add
                    </button>
                  </span>
                </form>
              </div>
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
