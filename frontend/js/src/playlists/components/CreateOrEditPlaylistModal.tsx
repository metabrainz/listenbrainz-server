import * as React from "react";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";
import { omit, isEqual } from "lodash";
import { Link } from "react-router";
import CreatableSelect from "react-select/creatable";
import {
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  getPlaylistExtension,
  getPlaylistId,
  getPlaylistTags,
  isPlaylistOwner,
  MAX_PLAYLIST_TAG_LENGTH,
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
  const originalTags = React.useMemo(() => getPlaylistTags(playlist), [
    playlist,
  ]);
  const [playlistTags, setPlaylistTags] = React.useState<string[]>(
    originalTags
  );
  const collaboratorsWithoutOwner = collaborators.filter(
    (username) => username.toLowerCase() !== currentUser.name
  );

  const [ownerPlaylistTagOptions, setOwnerPlaylistTagOptions] = React.useState<
    { value: string; label: string }[]
  >([]);

  React.useEffect(() => {
    if (!currentUser?.name || !currentUser?.auth_token) {
      setOwnerPlaylistTagOptions([]);
      return () => {};
    }

    let cancelled = false;

    const fetchTags = async () => {
      try {
        const response = await APIService.getUserPlaylistTags(
          currentUser.name,
          currentUser.auth_token
        );

        if (cancelled) return;

        setOwnerPlaylistTagOptions(
          (response?.tags ?? []).map(({ tag }) => ({
            value: tag,
            label: tag,
          }))
        );
      } catch (error) {
        console.error(error);
        if (!cancelled) {
          setOwnerPlaylistTagOptions([]);
        }
      }
    };

    fetchTags();

    return () => {
      cancelled = true;
    };
  }, [currentUser?.name, currentUser?.auth_token]);

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
    event.preventDefault();
    const normalize = (tags: string[]) =>
      Array.from(
        new Set(
          tags
            .map((t) => t.trim())
            .filter(Boolean)
            .map((t) => t.toLowerCase())
        )
      );
    try {
      let newPlaylist: JSPFPlaylist | undefined;
      if (isEdit) {
        newPlaylist = await editPlaylist();
      } else {
        // Creating a new playlist
        newPlaylist = await createPlaylist();
      }
      let playlistToResolve = newPlaylist;
      const authToken = currentUser?.auth_token;
      if (newPlaylist && authToken) {
        const newPlaylistId = getPlaylistId(newPlaylist);
        if (newPlaylistId) {
          const nextTags = normalize(playlistTags);
          const prevTags = normalize(originalTags);
          const toAdd = nextTags.filter((t) => !prevTags.includes(t));
          const toRemove = prevTags.filter((t) => !nextTags.includes(t));

          if (toAdd.length) {
            await APIService.addPlaylistTags(authToken, newPlaylistId, toAdd);
          }
          if (toRemove.length) {
            await Promise.all(
              toRemove.map((t) =>
                APIService.removePlaylistTag(authToken, newPlaylistId, t)
              )
            );
          }
          // Re-fetch so returned JSPF includes tags in additional_metadata (and
          // other metadata the edit payload does not resend).
          try {
            const response = await APIService.getPlaylist(
              newPlaylistId,
              authToken
            );
            const jspf: JSPFObject = await response.json();
            playlistToResolve = jspf.playlist;
          } catch (err) {
            console.error(err);
            const ext = getPlaylistExtension(newPlaylist);
            playlistToResolve = {
              ...newPlaylist,
              extension: {
                ...newPlaylist.extension,
                [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: {
                  ...ext,
                  public: ext?.public ?? true,
                  additional_metadata: {
                    ...ext?.additional_metadata,
                    tags: nextTags,
                  },
                },
              },
            } as JSPFPlaylist;
          }
        }
      }
      if (playlistToResolve) {
        if (isEdit) {
          toast.success(
            <ToastMsg
              title="Saved playlist"
              message={`Saved playlist ${playlistToResolve.title}`}
            />,
            { toastId: "saved-playlist" }
          );
        } else {
          const newPlaylistId = getPlaylistId(playlistToResolve);
          toast.success(
            <ToastMsg
              title="Created playlist"
              message={
                <>
                  Created new {isPublic ? "public" : "private"} playlist{" "}
                  <Link to={`/playlist/${newPlaylistId}/`}>
                    {playlistToResolve.title}
                  </Link>
                </>
              }
            />,
            { toastId: "create-playlist-success" }
          );
        }
      }
      modal.resolve(playlistToResolve);
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

        <div className="mb-4">
          <label
            className="form-label"
            style={{ display: "block" }}
            htmlFor="playlist-tags"
          >
            Tags
          </label>
          <CreatableSelect
            inputId="playlist-tags"
            isMulti
            isClearable={false}
            placeholder="Add tag"
            value={playlistTags.map((t) => ({ value: t, label: t }))}
            options={ownerPlaylistTagOptions}
            onChange={(values) => {
              const tags = (values ?? []).map((v) => v.value);
              if (tags.some((t) => t.trim().length > MAX_PLAYLIST_TAG_LENGTH)) {
                toast.error(
                  <ToastMsg
                    title="Tag"
                    message={`Keep the tag length less than ${MAX_PLAYLIST_TAG_LENGTH} chars.`}
                  />,
                  { toastId: "playlist-tag-length-error" }
                );
                return;
              }
              setPlaylistTags(tags);
            }}
            classNamePrefix="lb-tags"
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
