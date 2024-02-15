import * as React from "react";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import { omit } from "lodash";
import {
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  getPlaylistExtension,
  getPlaylistId,
  isPlaylistOwner,
} from "../utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import UserSearch from "../../common/UserSearch";
import NamePill from "../../personal-recommendations/NamePill";
import { ToastMsg } from "../../notifications/Notifications";

type CreateOrEditPlaylistModalProps = {
  playlist?: JSPFPlaylist;
  initialTracks?: JSPFTrack[];
};

export default NiceModal.create((props: CreateOrEditPlaylistModalProps) => {
  const modal = useModal();
  const closeModal = React.useCallback(() => {
    modal.hide();
    setTimeout(modal.remove, 200);
  }, [modal]);

  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { playlist, initialTracks } = props;
  const customFields = getPlaylistExtension(props.playlist);
  const playlistId = getPlaylistId(playlist);
  const isEdit = Boolean(playlistId);

  const [name, setName] = React.useState(playlist?.title ?? "");
  const [description, setDescription] = React.useState(
    playlist?.annotation ?? ""
  );
  const [isPublic, setIsPublic] = React.useState(customFields?.public ?? true);
  const [collaborators, setCollaborators] = React.useState<string[]>(
    customFields?.collaborators ?? []
  );
  const collaboratorsWithoutOwner = collaborators.filter(
    (username) => username.toLowerCase() !== currentUser.name
  );

  const createPlaylist = React.useCallback(async (): Promise<
    JSPFPlaylist | undefined
  > => {
    // Creating a new playlist
    if (!currentUser?.auth_token) {
      toast.error(
        <ToastMsg
          title="Error"
          message="You must be logged in for this operation"
        />,
        { toastId: "auth-error" }
      );
      return undefined;
    }
    // Owner can't be collaborator

    const newPlaylist: JSPFObject = {
      playlist: {
        // Th following 4 fields to satisfy TS type
        creator: currentUser?.name,
        identifier: "",
        date: "",
        track: initialTracks ?? [],
        title: name,
        annotation: description,
        extension: {
          [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
            public: isPublic,
            collaborators: collaboratorsWithoutOwner,
          },
        },
      },
    };
    try {
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
        // Fetch the newly created playlist and return it
        const response = await APIService.getPlaylist(
          newPlaylistId,
          currentUser.auth_token
        );
        const JSPFObject: JSPFObject = await response.json();
        return JSPFObject.playlist;
      } catch (error) {
        console.error(error);
        return newPlaylist.playlist;
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not create playlist"
          message={`Something went wrong: ${error.toString()}`}
        />,
        { toastId: "create-playlist-error" }
      );
      return undefined;
    }
  }, [
    currentUser,
    name,
    description,
    isPublic,
    collaboratorsWithoutOwner,
    initialTracks,
    APIService,
  ]);

  const editPlaylist = React.useCallback(async (): Promise<
    JSPFPlaylist | undefined
  > => {
    // Editing an existing playlist
    if (!currentUser?.auth_token) {
      toast.error(
        <ToastMsg
          title="Error"
          message="You must be logged in for this operation"
        />,
        { toastId: "auth-error" }
      );
      return undefined;
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
      return undefined;
    }

    if (!isPlaylistOwner(playlist, currentUser)) {
      toast.error(
        <ToastMsg
          title="Not allowed"
          message="Only the owner of a playlist is allowed to modify it"
        />,
        { toastId: "auth-error" }
      );
      return undefined;
    }
    try {
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

      toast.success(
        <ToastMsg
          title="Saved playlist"
          message={`Saved playlist ${playlist.title}`}
        />,
        { toastId: "saved-playlist" }
      );

      return editedPlaylist;
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not edit playlist"
          message={`Something went wrong: ${error.toString()}`}
        />,
        { toastId: "create-playlist-error" }
      );
      return undefined;
    }
  }, [
    playlist,
    playlistId,
    currentUser,
    name,
    description,
    isPublic,
    collaboratorsWithoutOwner,
    APIService,
  ]);

  const onSubmit = async (event: React.SyntheticEvent) => {
    try {
      let newPlaylist;
      if (isEdit) {
        newPlaylist = await editPlaylist();
      } else {
        // Creating a new playlist
        newPlaylist = await createPlaylist();
      }
      modal.resolve(newPlaylist);
      closeModal();
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
    setCollaborators(
      collaborators.filter((collabName) => collabName !== username)
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
                onChange={(event) => setName(event.target.value)}
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
                onChange={(event) => setDescription(event.target.value)}
              />
            </div>
            <div className="checkbox">
              <label>
                <input
                  id="isPublic"
                  type="checkbox"
                  checked={isPublic}
                  name="isPublic"
                  onChange={(event) => setIsPublic(event.target.checked)}
                />
                &nbsp;Make playlist public
              </label>
            </div>

            <div className="form-group">
              <div>
                <label style={{ display: "block" }} htmlFor="collaborators">
                  Collaborators
                </label>
                <div id="collaborators">
                  {collaborators.map((user) => {
                    return (
                      <NamePill
                        key={user}
                        title={user}
                        // eslint-disable-next-line react/jsx-no-bind
                        closeAction={removeCollaborator.bind(this, user)}
                      />
                    );
                  })}
                </div>
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
              onClick={onSubmit}
            >
              {isEdit ? "Save" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
});
