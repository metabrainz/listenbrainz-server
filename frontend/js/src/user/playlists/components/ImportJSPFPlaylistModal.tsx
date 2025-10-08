import * as React from "react";
import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Button, Form, Modal } from "react-bootstrap";
import { toast } from "react-toastify";

import { Link } from "react-router";
import { set } from "lodash";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { ToastMsg } from "../../../notifications/Notifications";
import { MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION } from "../../../playlists/utils";

const acceptExtensions = ["jspf", "json", "xspf"];
const acceptExtensionsWithDot = acceptExtensions
  .map((ext) => `.${ext}`)
  .join(", ");

export default NiceModal.create(() => {
  const modal = useModal();

  const { currentUser, APIService } = React.useContext(GlobalAppContext);

  const [fileError, setFileError] = React.useState<string | JSX.Element | null>(
    null
  );
  const [fileContent, setFileContent] = React.useState<JSPFObject | null>(null);
  const [makePrivate, setMakePrivate] = React.useState(false);

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
        set(
          fileContent,
          `playlist.extension["${MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION}"].public`,
          !makePrivate
        );
        // @ts-expect-error: We know this field is wrongly named when parsing XSPF files
        if (fileContent.playlist.tracks && !fileContent.playlist.track) {
          // @ts-expect-error
          fileContent.playlist.track = fileContent.playlist.tracks;
          // @ts-expect-error
          delete fileContent.playlist.tracks;
        }
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
  }, [currentUser.auth_token, fileContent, makePrivate, APIService]);

  const checkFileContent = (
    selectedFile: File | undefined,
    fileExtension: string
  ): void => {
    // Checks if the file is a valid JSON file
    // Note: This function does not check if the file is a valid JSPF file
    const reader = new FileReader();

    reader.onload = async (e: ProgressEvent<FileReader>) => {
      try {
        let jsonData;
        if (fileExtension === "xspf") {
          const { parse } = await import("xspf-js");
          jsonData = parse(e.target?.result);
        } else {
          jsonData = JSON.parse(e.target?.result as string);
        }
        // If valid JSON, set the new playlist state
        setFileContent(jsonData);
      } catch (error) {
        setFileError(
          <>
            Error parsing file: Please select a valid file (
            {acceptExtensionsWithDot}).
            <br />
            {error.toString()}
          </>
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

    // Check if the file has a valid extension
    if (selectedFile) {
      const fileExtension = selectedFile?.name.split(".").pop()?.toLowerCase();
      if (!fileExtension || !acceptExtensions.includes(fileExtension)) {
        setFileError(
          `Invalid file format. Please select a valid file (${acceptExtensionsWithDot}).`
        );

        return;
      }
      // Check if the file content is in valid JSON format and set the new playlist state
      checkFileContent(selectedFile, fileExtension);
    }
  };

  const onSubmit = async (event: React.SyntheticEvent) => {
    event.preventDefault();
    try {
      const newPlaylist = await createPlaylist();
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
      <Form validated={fileContent !== null} onSubmit={onSubmit}>
        <Modal.Body>
          <Form.Group className="mb-3" controlId="playlistFile">
            <Form.Label>
              Choose or drop a file with .json, .jspf or .xspf extension
            </Form.Label>
            <Form.Control
              type="file"
              className="form-control"
              accept={acceptExtensionsWithDot}
              onChange={handleFileChange}
              required
              isInvalid={fileError !== null}
            />
            <Form.Control.Feedback type="invalid">
              {fileError}
            </Form.Control.Feedback>
          </Form.Group>
          <Form.Group className="mb-3" controlId="makePrivate">
            <Form.Check
              type="checkbox"
              checked={makePrivate}
              onChange={() => setMakePrivate(!makePrivate)}
              label="Make the playlist private"
            />
          </Form.Group>
          <Form.Text>
            For information on the JSPF playlist format, please visit{" "}
            <a href="https://musicbrainz.org/doc/jspf">
              musicbrainz.org/doc/jspf
            </a>
          </Form.Text>
        </Modal.Body>
        <Modal.Footer>
          <Button type="button" variant="secondary" onClick={modal.hide}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={!currentUser?.auth_token || fileContent === null}
          >
            Import
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
});
