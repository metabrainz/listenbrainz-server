import * as React from "react";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";
import { omit, isEqual } from "lodash";
import { Link } from "react-router";
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
  coverArtGridOptions?: CoverArtGridOptions[];
  currentCoverArt?: CoverArtGridOptions;
};

export default NiceModal.create((props: CreateOrEditPlaylistModalProps) => {
  const modal = useModal();

  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const {
    playlist,
    initialTracks,
    coverArtGridOptions,
    currentCoverArt,
  } = props;
  const customFields = getPlaylistExtension(props.playlist);
  const playlistId = getPlaylistId(playlist);
  const isEdit = Boolean(playlistId);

  const [name, setName] = React.useState(playlist?.title ?? "");
  const [description, setDescription] = React.useState(
    playlist?.annotation ?? ""
  );
  const [selectedCoverArt, setSelectedCoverArt] = React.useState(
    currentCoverArt ?? coverArtGridOptions?.[0]
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
              <Link to={`/playlist/${newPlaylistId}/`}>{name}</Link>
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
            last_modified_at: new Date().toISOString(),
            additional_metadata: {
              cover_art: selectedCoverArt,
            },
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
    selectedCoverArt,
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
      modal.hide();
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
    if (!disabled && !collaborators.includes(user)) {
      setCollaborators([...collaborators, user]);
    }
  };

  return (
    <Modal
      {...bootstrapDialog(modal)}
      title="CreateOrEditPlaylistModal"
      aria-labelledby="CreateOrEditPlaylistModalLabel"
      id=""
    >
      <Modal.Header closeButton>
        <Modal.Title id="CreateOrEditPlaylistModalLabel">
          {isEdit ? "Edit" : "Create"} playlist
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div className="mb-4">
          <label className="form-label" htmlFor="playlistName">
            Name
          </label>
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

        <div className="mb-4">
          <label className="form-label" htmlFor="playlistdescription">
            Description
          </label>
          <textarea
            className="form-control"
            id="playlistdescription"
            placeholder="Description"
            value={description}
            name="description"
            onChange={(event) => setDescription(event.target.value)}
          />
        </div>
        {isEdit && coverArtGridOptions && (
          <div className="mb-4">
            <label className="form-label" htmlFor="artwork">
              Cover Art
            </label>
            <div className="cover-art-grid">
              {coverArtGridOptions?.map((option, index) => (
                <label className="cover-art-option">
                  <input
                    type="radio"
                    name="artwork"
                    value={`artwork-${option.dimension}-${option.layout}`}
                    key={`artwork-${option.dimension}-${option.layout}`}
                    className="cover-art-radio"
                    checked={isEqual(selectedCoverArt, option)}
                    onChange={() => setSelectedCoverArt(option)}
                  />
                  <img
                    height={80}
                    width={80}
                    src={`/static/img/playlist-cover-art/cover-art_${option.dimension}-${option.layout}.svg`}
                    alt={`Cover art option ${option.dimension}-${option.layout}`}
                    className="cover-art-image"
                  />
                </label>
              ))}
            </div>
          </div>
        )}
        <div className="form-check checkbox">
          <input
            id="isPublic"
            type="checkbox"
            className="form-check-input"
            checked={isPublic}
            name="isPublic"
            onChange={(event) => setIsPublic(event.target.checked)}
          />
          <label className="form-check-label" htmlFor="isPublic">
            &nbsp;Make playlist public
          </label>
        </div>

        <div className="mb-4">
          <div>
            <label
              className="form-label"
              style={{ display: "block" }}
              htmlFor="collaborators"
            >
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
      </Modal.Body>
      <Modal.Footer>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={modal.hide}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={!currentUser?.auth_token}
          onClick={onSubmit}
        >
          {isEdit ? "Save" : "Create"}
        </button>
      </Modal.Footer>
    </Modal>
  );
});
