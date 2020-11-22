import * as React from "react";

type CreateOrEditPlaylistModalProps = {
  playlist?: Playlist;
  onSubmit: (
    name: string,
    description: string,
    isPublic: boolean,
    collaborators: string[],
    id?: string
  ) => void;
};

type CreateOrEditPlaylistModalState = {
  name: string;
  description: string;
  isEdit: boolean;
  isPublic: boolean;
  collaborators: string[];
};

export default class CreateOrEditPlaylistModal extends React.Component<
  CreateOrEditPlaylistModalProps,
  CreateOrEditPlaylistModalState
> {
  constructor(props: CreateOrEditPlaylistModalProps) {
    super(props);

    this.state = {
      name: props.playlist?.title ?? "",
      description: props.playlist?.description ?? "",
      isEdit: Boolean(props.playlist?.id),
      isPublic: props.playlist ? props.playlist.public : true,
      collaborators: props.playlist?.collaborators || [],
    };
  }

  submit = (event: React.SyntheticEvent) => {
    event.preventDefault();
    const { onSubmit, playlist } = this.props;
    const { name, description, isPublic, collaborators } = this.state;

    // VALIDATION PLEASE !
    onSubmit(name, description, isPublic, collaborators, playlist?.id);
  };

  handleInputChange = (event: React.SyntheticEvent) => {
    const { target } = event;
    const value = target.type === "checkbox" ? target.checked : target.value;
    const { name } = target;

    this.setState({
      [name]: value,
    });
  };

  render() {
    const { name, description, isEdit, isPublic, collaborators } = this.state;
    return (
      <div
        className="modal fade"
        id="playlistModal"
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
                    type="checkbox"
                    checked={isPublic}
                    name="isPublic"
                    onChange={this.handleInputChange}
                  />
                  &nbsp;public playlist
                </label>
                <div className="form-group">
                  <label>
                    Collaborators
                    {collaborators.map((collaborator) => {
                      return <div>{collaborator.name ?? collaborator}</div>;
                    })}
                  </label>
                </div>
              </div>
              <div>Something here for adding/removing collaborators</div>
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
