import * as React from "react";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";

import { Link } from "react-router-dom";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";

export default NiceModal.create(() => {
  const modal = useModal();
  const closeModal = React.useCallback(() => {
    modal.hide();
    setTimeout(modal.remove, 200);
  }, [modal]);

  const { currentUser, APIService } = React.useContext(GlobalAppContext);

  const [fileError, setFileError] = React.useState<string | null>(null);
  const [fileContent, setFileContent] = React.useState<JSPFObject | null>(null);

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
      if (fileContent) {
        const newPlaylistId = await APIService.createPlaylist(
          currentUser?.auth_token,
          fileContent
        );
        toast.success(
          <ToastMsg
            title="Created playlist"
            message={
              <>
                Created a new playlist with ID:
                <Link to={`/playlist/${newPlaylistId}`}>{newPlaylistId}</Link>
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

          return undefined;
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
  }, [currentUser, fileContent, APIService]);

  const checkFileContent = (selectedFile: File | undefined): void => {
    // Checks if the file is a valid JSON file
    // Note: This function does not check if the file is a valid JSPF file
    const reader = new FileReader();

    reader.onload = (e: ProgressEvent<FileReader>): void => {
      try {
        // If valid JSON, set the new playlist state
        const jsonData = JSON.parse(e.target?.result as string);
        setFileContent(jsonData);
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
      const newPlaylist = await createPlaylist();
      if (!newPlaylist) {
        return;
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
              Import playlist
            </h4>
          </div>
          <div className="modal-body">
            <div className="form-group">
              <label htmlFor="playlistFile">
                Choose or drop a file with .json or .jspf extension
              </label>
              <input
                type="file"
                className=""
                id="playlistFile"
                accept=".jspf, .json"
                onChange={handleFileChange}
              />
              {fileError && <div className="has-error">{fileError}</div>}
              <p className="help-block">
                For information on the JSPF playlist format, please visit{" "}
                <a href="https://musicbrainz.org/doc/jspf">
                  musicbrainz.org/doc/jspf
                </a>
              </p>
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
              disabled={!currentUser?.auth_token || fileContent === null}
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
