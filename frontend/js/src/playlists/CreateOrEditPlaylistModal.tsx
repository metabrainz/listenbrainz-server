import * as React from "react";
import { MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION, getPlaylistExtension, getPlaylistId, isPlaylistOwner } from "./utils";
import GlobalAppContext from "../utils/GlobalAppContext";
import UserSearch from "./UserSearch";
import NamePill from "../personal-recommendations/NamePill";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import { ToastMsg } from "../notifications/Notifications";
import { omit } from "lodash";
import APIService from "../utils/APIService";

type CreateOrEditPlaylistModalProps = {
  playlist?: JSPFPlaylist;
};

export default NiceModal.create((props: CreateOrEditPlaylistModalProps) => {
  const modal = useModal();
  const closeModal = React.useCallback(() => {
    modal.hide();
    setTimeout(modal.remove, 500);
  }, [modal]);

  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { playlist } = props;
  const customFields = getPlaylistExtension(props.playlist);
  const playlistId = getPlaylistId(playlist);
  const isEdit = Boolean(playlistId);

  
  const [name, setName] = React.useState(playlist?.title ?? "");
  const [description, setDescription] = React.useState(playlist?.annotation ?? "");
  const [isPublic, setIsPublic] = React.useState(customFields?.public ?? true);
  const [collaborators, setCollaborators] = React.useState<string[]>(customFields?.collaborators ?? []);
  const collaboratorsWithoutOwner = collaborators.filter(
    (username) => username.toLowerCase() !== currentUser.name
  );
  
const createPlaylist = React.useCallback(async () => {
  // Creating a new playlist
  if (!currentUser?.auth_token) {
    toast.error(
      <ToastMsg
        title="Error"
        message="You must be logged in for this operation"
      />,
      { toastId: "auth-error" }
    );
    return;
  }
  // Owner can't be collaborator
  
  const newPlaylist: JSPFObject = {
    playlist: {
      // Th following 4 fields to satisfy TS type
      creator: currentUser?.name,
      identifier: "",
      date: "",
      track: [],

      title:name,
      annotation: description,
      extension: {
        [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
          public: isPublic,
          collaborators: collaboratorsWithoutOwner,
        },
      },
    },
  };
  const newPlaylistId = await APIService.createPlaylist(
    currentUser?.auth_token,
    newPlaylist
  );
  toast.success(
    <ToastMsg
      title="Created playlist"
      message={
        <>
          Created new {isPublic ? "public" : "private"} playlist{" "}
          <a href={`/playlist/${newPlaylistId}`}>{name}</a>
        </>
      }
    />,
    { toastId: "create-playlist-success" }
  );
  try {
    // Fetch the newly created playlist and addreturn it
    const response = await APIService.getPlaylist(
      newPlaylistId,
      currentUser.auth_token
    )
    const JSPFObject: JSPFObject = await response.json();
    modal.resolve(JSPFObject.playlist)
  } catch (error) {
    modal.resolve(newPlaylist.playlist)
  }
  closeModal();

},[currentUser,name, description,isPublic,collaboratorsWithoutOwner])

const editPlaylist = React.useCallback(async () => {
  // Editing an existing playlist
  if (!currentUser?.auth_token) {
    toast.error(
      <ToastMsg
        title="Error"
        message="You must be logged in for this operation"
      />,
      { toastId: "auth-error" }
    );
    return;
  }

  if (!playlist || !playlistId) {
    toast.error(
      <ToastMsg
        title="Error"
        message={
          "Trying to edit a playlist without an id. This shouldn't have happened, please contact us with the error message."
        }
      />,
      { toastId: "edit-playlist-error" }
    );
    return;
  }
  
    if (!isPlaylistOwner(playlist, currentUser)) {
      toast.error(
        <ToastMsg
          title="Not allowed"
          message="Only the owner of a playlist is allowed to modify it"
        />,
        { toastId: "auth-error" }
      );
      return;
    }

    // Owner can't be collaborator
    const collaboratorsWithoutOwner = collaborators.filter(
      (username) => username.toLowerCase() !== playlist.creator.toLowerCase()
    );
    const editedPlaylist: JSPFPlaylist = {
      ...playlist,
      annotation: description,
      title: name,
      extension: {
        [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
          public: isPublic,
          collaborators: collaboratorsWithoutOwner,
        },
      },
    };

    await APIService.editPlaylist(currentUser.auth_token, playlistId, {
      playlist: omit(editedPlaylist, "track") as JSPFPlaylist,
    });

    modal.resolve(editedPlaylist);
    toast.success(
      <ToastMsg
        title="Saved playlist"
        message={`Saved playlist ${playlist.title}`}
      />,
      { toastId: "saved-playlist" }
    );
    closeModal();
},[playlist,playlistId,currentUser,name, description,isPublic,collaboratorsWithoutOwner]);
  
  const onSubmit = async (event: React.SyntheticEvent) => {
    event.preventDefault();

    try {
      if(isEdit){
        await editPlaylist()
      } else {
        // Creating a new playlist
        await createPlaylist();
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Something went wrong"
          message={<>We could not save your playlist: {error.toString()}</>}
        />,
        { toastId: "save-playlist-error" }
      );
    }
  };
  
  const removeCollaborator = (username: string): void => {
    setCollaborators(collaborators.filter(
        (collabName) => collabName !== username
      )
    );
  };

  const addCollaborator = (user: string): void => {
    const disabled =
      !user ||
      (isEdit
        ? playlist?.creator.toLowerCase() === user.toLowerCase()
        : currentUser.name.toLowerCase() === user.toLowerCase());
    if (!disabled && collaborators.includes(user)) {
      setCollaborators([...collaborators, user]);
    }
  };
  
  return (
    <div
      className={`modal fade ${modal.visible ? "in" : ""}`}
      id="CreateOrEditPlaylistModal"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="playlistModalLabel"
      data-backdrop="static"
    >
      <div className="modal-dialog" role="document">
        <form className="modal-content"  onSubmit={onSubmit}>
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
                onChange={event => setName(event.target.value)}
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
                onChange={event => setDescription(event.target.value)}
              />
            </div>
            <div className="checkbox">
              <label>
                <input
                  id="isPublic"
                  type="checkbox"
                  checked={isPublic}
                  name="isPublic"
                  onChange={event => setIsPublic(event.target.checked)}
                />
                &nbsp;Make playlist public
              </label>
            </div>

            <div className="form-group">
              <div>
                <label style={{ display: "block" }}>Collaborators</label>

                {collaborators.map((user) => {
                  return (
                    <NamePill
                      key={user}
                      title={user}
                      closeAction={removeCollaborator.bind(this, user)}
                    />
                  );
                })}
              </div>

              <UserSearch
                onSelectUser={addCollaborator}
                placeholder="Add collaborator"
                clearOnSelect
              />
            </div>
          </div>
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-default"
              data-dismiss="modal"
              onClick={closeModal}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              data-dismiss="modal"
              disabled={!currentUser?.auth_token}
            >
              {isEdit ? "Save" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
});