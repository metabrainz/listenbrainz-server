import * as React from "react";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import { omit, set } from "lodash";

import {
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  getPlaylistExtension,
  getPlaylistId,
  isPlaylistOwner,
} from "../utils";

import GlobalAppContext from "../../utils/GlobalAppContext";
import { ToastMsg } from "../../notifications/Notifications";

type ImportPlaylistModalProps = {
  playlist?: JSPFPlaylist;
  initialTracks?: JSPFTrack[];
};

export default NiceModal.create((props: ImportPlaylistModalProps) => {
  const modal = useModal();
  const closeModal = React.useCallback(() => {
    modal.hide();
    setTimeout(modal.remove, 3000);
  }, [modal]);

  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { playlist, initialTracks } = props;
  const playlistId = getPlaylistId(playlist);

  const [fileError, setFileError] = React.useState<string | null>(null);
  const [newPlaylist, setNewPlaylist] = React.useState<JSPFObject | null>(null);

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
    try {
      if (newPlaylist) {
        const newPlaylistId = await APIService.createPlaylist(
          currentUser?.auth_token,
          newPlaylist
        );

        toast.success(
          <ToastMsg
            title="Created playlist"
            message={
              <>
                Created a new playlist with ID:
                <a href={`/playlist/${newPlaylistId}`}>{newPlaylistId}</a>
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
      } else {
        return undefined;
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
  }, [currentUser, newPlaylist, APIService]);

  const checkFileContent = (selectedFile: File | undefined): void => {
    // Checks if the file is a valid JSON file
    // Note: This function does not check if the file is a valid JSPF file
    const reader = new FileReader();

    reader.onload = (e: ProgressEvent<FileReader>): void => {
      try {
        // If valid JSON, set the new playlist state
        const jsonData = JSON.parse(e.target?.result as string);
        setNewPlaylist(jsonData);
      } catch (error) {
        setFileError("Error parsing JSON: Please select a valid JSON file.");
      }
    };
    if (selectedFile) {
      reader.readAsText(selectedFile);
    }
  };

  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ): void => {
    const selectedFile = event.target.files?.[0];

    // Clear previous error when a new file is selected
    setFileError(null);

    // Check if the file has a valid extension
    if (selectedFile) {
      const fileExtension = selectedFile?.name.split(".").pop()?.toLowerCase();
      if (fileExtension !== "jspf" && fileExtension !== "json") {
        setFileError("Invalid file format. Please select a valid file.");

        return;
      }
      // Check if the file content is in valid JSON format and set the new playlist state
      checkFileContent(selectedFile);
    }
  };

  const onSubmit = async (event: React.SyntheticEvent) => {
    try {
      createPlaylist();
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

  return (
    <div
      className={`modal fade ${modal.visible ? "in" : ""}`}
      id="ImportPlaylistModal"
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
              Create playlist
            </h4>
          </div>
          <div className="modal-body">
            <div className="form-group">
              <label htmlFor="playlistFile">
                Drop the file having JSON or JSPF format
              </label>
              <input
                type="file"
                className=""
                id="playlistFile"
                accept=".jspf, .json"
                onChange={handleFileChange}
              />
              {fileError && <div className="has-error">{fileError}</div>}
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
              disabled={!currentUser?.auth_token || fileError !== null}
              onClick={onSubmit}
            >
              Import
            </button>
          </div>
        </form>
      </div>
    </div>
  );
});
