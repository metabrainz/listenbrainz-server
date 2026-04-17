import * as React from "react";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import { toast } from "react-toastify";

import { Link } from "react-router";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";

export default NiceModal.create(() => {
  const modal = useModal();

  const { currentUser, APIService } = React.useContext(GlobalAppContext);

  const [fileError, setFileError] = React.useState<string | null>(null);
  const [fileContent, setFileContent] = React.useState<JSPFObject | null>(null);
  const [xspfContent, setXspfContent] = React.useState<string | null>(null);
  const [isXspf, setIsXspf] = React.useState<boolean>(false);

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

  const checkXSPFFileContent = (selectedFile: File | undefined): void => {
    // Reads the file as plain text and stores the raw XSPF XML content
    const reader = new FileReader();

    reader.onload = async (e: ProgressEvent<FileReader>): Promise<void> => {
      const textData = (e.target?.result as string) || "";
      if (!textData.trim()) {
        setFileError("The selected XSPF file is empty.");
        setXspfContent(null);
        return;
      }
      try {
        const { parse } = await import("xspf-js");
        parse(textData);
        setFileError(null);
        setXspfContent(textData);
      } catch (error) {
        setXspfContent(null);
        setFileError(
          error instanceof Error
            ? `Invalid XSPF file: ${error.message}`
            : "Invalid XSPF file: could not parse the playlist XML."
        );
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
    setFileContent(null);
    setXspfContent(null);
    setIsXspf(false);

    // Check if the file has a valid extension
    if (selectedFile) {
      const fileExtension = selectedFile?.name.split(".").pop()?.toLowerCase();
      if (fileExtension === "jspf" || fileExtension === "json") {
        // JSPF/JSPF-as-JSON import
        checkFileContent(selectedFile);
      } else if (fileExtension === "xspf") {
        // XSPF (XML) import
        setIsXspf(true);
        checkXSPFFileContent(selectedFile);
      } else {
        setFileError(
          "Invalid file format. Please select a .jspf, .json, or .xspf file."
        );
      }
    }
  };

  const onSubmit = async (event: React.SyntheticEvent) => {
    event.preventDefault();
    try {
      let newPlaylist: JSPFPlaylist | undefined;

      if (isXspf) {
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
        if (!xspfContent) {
          setFileError(
            "No XSPF content found. Please select a valid XSPF file."
          );
          return;
        }

        const newPlaylistResponse = await APIService.importXSPFPlaylistTracks(
          currentUser.auth_token,
          xspfContent
        );

        newPlaylist = newPlaylistResponse.playlist;

        toast.success(
          <ToastMsg
            title="Imported XSPF playlist"
            message={
              <>
                Imported a playlist:
                <Link to={`/playlist/${newPlaylistResponse.identifier}`}>
                  {newPlaylist.title}
                </Link>
              </>
            }
          />,
          { toastId: "import-xspf-playlist-success" }
        );
      } else {
        newPlaylist = await createPlaylist();
      }

      if (!newPlaylist) {
        return;
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

  return (
    <Modal
      {...bootstrapDialog(modal)}
      title="Import playlist"
      aria-labelledby="ImportPlaylistModalLabel"
      id="ImportPlaylistModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="ImportPlaylistModalLabel">Import playlist</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <div>
          <label className="form-label" htmlFor="playlistFile">
            Choose or drop a file with .json, .jspf, or .xspf extension
          </label>
          <input
            type="file"
            className="form-control"
            id="playlistFile"
            accept=".jspf, .json, .xspf"
            onChange={handleFileChange}
          />
        </div>
        {fileError && <div className="has-error">{fileError}</div>}
        <p className="form-text">
          For information on the JSPF playlist format, please visit{" "}
          <a
            href="https://musicbrainz.org/doc/jspf"
            target="_blank"
            rel="noopener noreferrer"
          >
            musicbrainz.org/doc/jspf
          </a>
        </p>
        <p className="form-text">
          You can also import playlists from XSPF files (
          <a
            href="https://www.xspf.org/"
            target="_blank"
            rel="noopener noreferrer"
          >
            xspf.org
          </a>
          ).
        </p>
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
          disabled={
            !currentUser?.auth_token ||
            (fileContent === null && xspfContent === null)
          }
          onClick={onSubmit}
        >
          Import
        </button>
      </Modal.Footer>
    </Modal>
  );
});
