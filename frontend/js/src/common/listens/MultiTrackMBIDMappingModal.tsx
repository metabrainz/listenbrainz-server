import NiceModal, { useModal } from "@ebay/nice-modal-react";
import {
  faArrowRightLong,
  faInfoCircle,
  faQuestionCircle,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { toast } from "react-toastify";
import Tooltip from "react-tooltip";
import Fuse from "fuse.js";
import ListenCard from "./ListenCard";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SearchAlbumOrMBID from "../../utils/SearchAlbumOrMBID";
import {
  getListenFromTrack,
  MBTrackWithAC,
} from "../../user/components/AddListenModal";
import { MBReleaseWithMetadata } from "../../user/components/AddAlbumListens";

type MatchingTracksResults = {
  [recording_msid: string]: MBTrackWithAC & {
    searchString: string;
  };
};

export type MultiTrackMBIDMappingModalProps = {
  releaseName: string;
  missingData: Array<MissingMBData>;
};

export default NiceModal.create(
  ({ missingData, releaseName }: MultiTrackMBIDMappingModalProps) => {
    const modal = useModal();
    const { APIService, currentUser } = React.useContext(GlobalAppContext);
    const { lookupMBRelease } = APIService;
    const { auth_token } = currentUser;

    const { resolve, visible } = modal;

    const [matchingTracks, setMatchingTracks] = React.useState<
      MatchingTracksResults
    >();
    const [selectedAlbumMBID, setSelectedAlbumMBID] = React.useState<string>();
    const [selectedAlbum, setSelectedAlbum] = React.useState<
      MBReleaseWithMetadata
    >();
    const [potentialTracks, setPotentialTracks] = React.useState<
      MBTrackWithAC[]
    >();

    const closeModal = React.useCallback(() => {
      modal.hide();
      document?.body?.classList?.remove("modal-open");
      setTimeout(modal.remove, 200);
    }, [modal]);

    React.useEffect(() => {
      const closeOnEscape = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          closeModal();
        }
      };
      window.addEventListener("keydown", closeOnEscape);
      return () => window.removeEventListener("keydown", closeOnEscape);
    }, [closeModal]);

    const handleError = React.useCallback(
      (error: string | Error, title?: string): void => {
        if (!error) {
          return;
        }
        toast.error(
          <ToastMsg
            title={title || "Error"}
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "linked-track-error" }
        );
      },
      []
    );

    const submitMBIDMapping = React.useCallback(
      async (event: React.FormEvent) => {
        if (event) {
          event.preventDefault();
        }
        if (!matchingTracks?.length || !auth_token) {
          return;
        }
        const promises: Promise<any>[] = [];
        // eslint-disable-next-line no-restricted-syntax
        for (const [recordingMSID, trackMetadata] of Object.entries(
          matchingTracks
        )) {
          // const selectedRecordingToListen = getListenFromSelectedRecording(
          //   trackMetadata
          // );
          // const recordingMBID =
          //   selectedRecordingToListen &&
          //   getRecordingMBID(selectedRecordingToListen);
          // if (recordingMBID) {
          //   promises.push(
          //     APIService.submitMBIDMapping(
          //       auth_token,
          //       recordingMSID,
          //       recordingMBID
          //     )
          //   );
          // }
        }
        try {
          await Promise.all(promises);
          toast.success(`You linked ${promises.length} tracks!`, {
            toastId: "linked-track",
          });

          resolve(matchingTracks);
          closeModal();
        } catch (error) {
          handleError(error, "Error while linking listens");
        }
      },
      [auth_token, closeModal, resolve, APIService, matchingTracks, handleError]
    );

    React.useEffect(() => {
      async function fetchTrackList(releaseMBID: string) {
        // Fetch the tracklist fron MusicBrainz
        try {
          const fetchedRelease = (await lookupMBRelease(
            releaseMBID,
            "recordings+artist-credits+release-groups"
          )) as MBReleaseWithMetadata;
          setSelectedAlbum(fetchedRelease);
          const newSelection = fetchedRelease.media
            .map(({ tracks }) => tracks as MBTrackWithAC[])
            .flat();
          setPotentialTracks(newSelection);
        } catch (error) {
          toast.error(`Could not load track list for ${releaseMBID}`);
        }
      }
      if (!selectedAlbumMBID) {
        setSelectedAlbum(undefined);
        setPotentialTracks([]);
      } else {
        fetchTrackList(selectedAlbumMBID);
      }
    }, [selectedAlbumMBID, lookupMBRelease]);

    React.useEffect(() => {
      if (!potentialTracks?.length) {
        return;
      }
      // Once we select an album and fetch the tracklist, we want to automatically match
      // listens to their corresponding track
      const fuzzysearch = new Fuse(potentialTracks, {
        keys: ["title", "artist-credit.name"],
      });
      const newMatchingTracks: MatchingTracksResults = {};
      missingData.forEach((missingDataItem) => {
        const stringToSearch = `${missingDataItem.recording_name} ${missingDataItem.artist_name}`;
        const matches = fuzzysearch.search(stringToSearch);
        if (matches[0]) {
          // We have a match
          newMatchingTracks[missingDataItem.recording_msid] = {
            ...matches[0].item,
            searchString: stringToSearch,
          };
        }
      });
      setMatchingTracks(newMatchingTracks);
    }, [missingData, potentialTracks]);

    if (!missingData) {
      return null;
    }
    const matchingTracksEntries =
      matchingTracks && Object.entries(matchingTracks);
    const hasMatches = Boolean(matchingTracksEntries?.length);
    const unmatchedItems =
      (hasMatches &&
        missingData.filter((md) => !matchingTracks?.[md.recording_msid])) ??
      [];

    return (
      <>
        <div
          className={`modal fade ${visible ? "in" : ""}`}
          style={visible ? { display: "block" } : {}}
          id="MultiTrackMBIDMappingModal"
          role="dialog"
          aria-labelledby="MultiTrackMBIDMappingModalLabel"
          data-backdrop="static"
        >
          <div className="modal-dialog" role="document">
            <Tooltip id="musicbrainz-helptext" type="light" multiline>
              Search for an album matching the tracks below.
              <br />
              Alternatively, you can search for a release or release-group usign
              the MusicBrainz search (musicbrainz.org/search). When you have
              found the one that matches your listens, copy its URL (link) into
              the field on this page.
            </Tooltip>
            <form className="modal-content" onSubmit={submitMBIDMapping}>
              <div className="modal-header">
                <button
                  type="button"
                  className="close"
                  onClick={closeModal}
                  aria-label="Close"
                >
                  <span aria-hidden="true">&times;</span>
                </button>
                <h4
                  className="modal-title"
                  id="MultiTrackMBIDMappingModalLabel"
                >
                  Link these Listens with MusicBrainz
                </h4>
              </div>
              <div className="modal-body">
                <p>
                  Sometimes ListenBrainz is unable to automatically link your
                  Listen with a MusicBrainz release or release group. Search by
                  album and artist name or paste a{" "}
                  <a href="https://musicbrainz.org/doc/About">MusicBrainz</a>{" "}
                  recording URL or MBID{" "}
                  <FontAwesomeIcon
                    icon={faQuestionCircle}
                    data-tip
                    data-for="musicbrainz-helptext"
                    size="sm"
                  />{" "}
                  below to link these Listens.
                </p>
                <small className="help-block">
                  <FontAwesomeIcon icon={faInfoCircle} />
                  &nbsp;
                  <a
                    href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html#user-statistics"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    How long until my stats reflect the change?
                  </a>
                </small>
                <h5>Search</h5>
                <div className="card listen-card">
                  <SearchAlbumOrMBID
                    onSelectAlbum={setSelectedAlbumMBID}
                    defaultValue={releaseName}
                  />
                </div>
                <hr />

                {/* {
                  <>
                    <ListenCard
                      listen={listenFromSelectedRecording}
                      showTimestamp={false}
                      showUsername={false}
                      compact
                      additionalActions={
                        <ListenControl
                          buttonClassName="btn-transparent"
                          text=""
                          title="Reset"
                          icon={faTimesCircle}
                          iconSize="lg"
                          action={() => setSelectedRecordings(undefined)}
                        />
                      }
                    />
                    <small className="help-block">
                      Recordings added to MusicBrainz within the last 4 hours
                      may temporarily look incomplete.
                      <a
                        href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html#mbid-mapper-musicbrainz-metadata-cache"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Click here to learn why.
                      </a>
                    </small>
                  </>
                } */}
                {hasMatches && matchingTracksEntries && (
                  <h4>
                    Matched {matchingTracksEntries.length} of{" "}
                    {missingData.length} listens on the release:
                  </h4>
                )}
                {selectedAlbum && (
                  <div className="header-with-line">
                    <a
                      href={`https://musicbrainz.org/release/${selectedAlbum.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <strong>{selectedAlbum.title}</strong>
                    </a>
                    {selectedAlbum.date && (
                      <span>
                        &nbsp;({new Date(selectedAlbum.date).getFullYear()})
                      </span>
                    )}
                    &nbsp;–&nbsp;
                    {selectedAlbum["artist-credit"]
                      ?.map((artist) => `${artist.name}${artist.joinphrase}`)
                      .join("")}
                    {selectedAlbum["release-group"]?.["primary-type"] && (
                      <small>
                        &nbsp;(
                        {selectedAlbum["release-group"]?.["primary-type"]})
                      </small>
                    )}
                  </div>
                )}

                {hasMatches &&
                  matchingTracksEntries &&
                  matchingTracksEntries.map(([recordingMBID, track]) => {
                    return (
                      <div className="flex" style={{ alignItems: "center" }}>
                        <div>{track.searchString}</div>
                        <FontAwesomeIcon
                          icon={faArrowRightLong}
                          style={{ flex: "0 1 50px" }}
                        />
                        <div style={{ flex: "2 1 0%" }}>
                          <ListenCard
                            compact
                            listen={getListenFromTrack(
                              track,
                              new Date(0),
                              selectedAlbum
                            )}
                            showTimestamp={false}
                            showUsername={false}
                          />
                        </div>
                      </div>
                    );
                  })}
                {unmatchedItems && unmatchedItems.length && (
                  <>
                    <h4>Unmatched items</h4>
                    {unmatchedItems.map((unmatched) => (
                      <div>
                        {[unmatched.recording_name, unmatched.artist_name].join(
                          " "
                        )}
                      </div>
                    ))}
                  </>
                )}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-default"
                  onClick={closeModal}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-success"
                  //   disabled={!selectedRecordings.length}
                >
                  Add mapping
                </button>
              </div>
            </form>
          </div>
        </div>
        {/* {visible && (
          <div className={`modal-backdrop poop fade ${visible ? "in" : ""}`} />
        )} */}
      </>
    );
  }
);
