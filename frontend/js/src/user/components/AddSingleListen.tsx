import React, {
  useEffect,
  useRef,
  useState,
  forwardRef,
  useImperativeHandle,
} from "react";
import {
  faChevronDown,
  faTimesCircle,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import ListenControl from "../../common/listens/ListenControl";
import ListenCard from "../../common/listens/ListenCard";
import SearchTrackOrMBID from "../../utils/SearchTrackOrMBID";
import { getListenFromRecording } from "./AddListenModal";
import ReleaseCard from "../../explore/fresh-releases/components/ReleaseCard";

interface AddSingleListenProps {
  onPayloadChange: (listens: Listen[]) => void;
  switchMode: (text: string) => void;
  initialText?: string;
  onSearchTextChange?: (text: string) => void;
}

const AddSingleListen = forwardRef(function AddSingleListen(
  {
    onPayloadChange,
    switchMode,
    initialText,
    onSearchTextChange,
  }: AddSingleListenProps,
  ref
) {
  const [selectedRecordings, setSelectedRecordings] = useState<
    MusicBrainzRecordingWithReleasesAndRGs[]
  >([]);
  const [selectedReleases, setSelectedReleases] = useState<{
    [recording_mbid: string]:
      | (MusicBrainzRelease & WithReleaseGroup)
      | undefined;
  }>({});

  const searchInputRef = useRef<SearchInputImperativeHandle>(null);

  const initialTextRef = useRef(initialText);
  React.useEffect(() => {
    // Trigger search manually if auto-switching from album to recording search
    if (initialText && initialTextRef.current !== initialText) {
      searchInputRef.current?.triggerSearch(initialText);
      initialTextRef.current = initialText;
    }
    return () => {
      initialTextRef.current = undefined;
    };
  }, [initialText]);

  useImperativeHandle(ref, () => ({
    reset: () => {
      setSelectedRecordings([]);
      setSelectedReleases({});
      searchInputRef.current?.reset();
    },
  }));

  const removeRecording = (recordingMBID: string) => {
    setSelectedRecordings((prevRecordings) =>
      prevRecordings.filter((rec) => rec.id !== recordingMBID)
    );
    setSelectedReleases((prevReleases) => {
      const copy = { ...prevReleases };
      delete copy[recordingMBID];
      return copy;
    });
  };

  const selectRecording = (
    newSelectedRecording: MusicBrainzRecordingWithReleasesAndRGs
  ) => {
    setSelectedRecordings((prevRecordings) => [
      ...prevRecordings,
      newSelectedRecording,
    ]);
    if (newSelectedRecording.releases?.length === 1) {
      setSelectedReleases((prevReleases) => ({
        ...prevReleases,
        [newSelectedRecording.id]: newSelectedRecording.releases[0],
      }));
    } else {
      setSelectedReleases((prevReleases) => {
        const copy = { ...prevReleases };
        delete copy[newSelectedRecording.id];
        return copy;
      });
    }
  };

  useEffect(() => {
    const listens = selectedRecordings.map((recording) =>
      getListenFromRecording(
        recording,
        new Date(),
        selectedReleases?.[recording.id]
      )
    );
    onPayloadChange(listens);
  }, [selectedRecordings, selectedReleases, onPayloadChange]);

  return (
    <div>
      <SearchTrackOrMBID
        ref={searchInputRef}
        expectedPayload="recording"
        onSelectRecording={selectRecording}
        switchMode={switchMode}
        requiredInput={selectedRecordings.length === 0}
        defaultValue={initialText}
        onSearchTextChange={onSearchTextChange}
      />
      <div className="track-info">
        <div className="content">
          {selectedRecordings?.map((recording, index) => {
            const listen = getListenFromRecording(
              recording,
              new Date(),
              selectedReleases?.[recording.id]
            );
            return (
              <div key={recording.id}>
                <ListenCard
                  listen={listen}
                  showTimestamp={false}
                  showUsername={false}
                  // eslint-disable-next-line react/jsx-no-useless-fragment
                  feedbackComponent={<></>}
                  compact
                  additionalActions={
                    <ListenControl
                      buttonClassName="btn btn-transparent"
                      text=""
                      title="Reset"
                      icon={faTimesCircle}
                      iconSize="lg"
                      action={() => {
                        removeRecording(recording.id);
                        searchInputRef?.current?.focus();
                      }}
                    />
                  }
                />
                {recording?.releases?.length > 1 && (
                  <>
                    <h5
                      data-bs-toggle="collapse"
                      data-bs-target={`#collapsible-${recording.id}`}
                      aria-controls={`collapsible-${recording.id}`}
                      className="header-with-line collapsed"
                      style={{
                        gap: "5px",
                        marginBottom: "0.5em",
                        alignItems: "center",
                        cursor: "pointer",
                      }}
                      id="select-release"
                    >
                      Choose from {recording?.releases?.length} releases&nbsp;
                      <small>(optional)</small>&nbsp;
                      <FontAwesomeIcon icon={faChevronDown} size="xs" />
                    </h5>
                    <div
                      className="collapse"
                      id={`collapsible-${recording.id}`}
                    >
                      <div className="form-text">
                        Too many choices? See more details{" "}
                        <a
                          href={`https://musicbrainz.org/recording/${recording.id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          on MusicBrainz
                        </a>
                        .
                      </div>
                      <div className="release-cards-grid">
                        {recording.releases.map((release) => {
                          const releaseGroup = release["release-group"];
                          return (
                            <span
                              data-bs-toggle="collapse"
                              data-bs-target={`#collapsible-${recording.id}`}
                              key={release.id}
                            >
                              <ReleaseCard
                                key={release.id}
                                onClick={() => {
                                  setSelectedReleases((prevReleases) => ({
                                    ...prevReleases,
                                    [recording.id]: release,
                                  }));
                                }}
                                releaseName={release.title}
                                releaseDate={release.date}
                                dateFormatOptions={{
                                  year: "numeric",
                                  month: "short",
                                }}
                                releaseMBID={release.id}
                                releaseGroupMBID={releaseGroup?.id}
                                artistCreditName={recording["artist-credit"]
                                  ?.map(
                                    (artist) =>
                                      `${artist.name}${artist.joinphrase}`
                                  )
                                  .join("")}
                                artistCredits={recording["artist-credit"].map(
                                  (ac) => ({
                                    artist_credit_name: ac.name,
                                    artist_mbid: ac.artist.id,
                                    join_phrase: ac.joinphrase,
                                  })
                                )}
                                artistMBIDs={recording["artist-credit"]?.map(
                                  (ac) => ac.artist.id
                                )}
                                releaseTypePrimary={
                                  releaseGroup?.["primary-type"]
                                }
                                releaseTypeSecondary={releaseGroup?.[
                                  "secondary-types"
                                ].join("+")}
                                caaID={null}
                                caaReleaseMBID={release.id}
                                showTags={false}
                                showArtist
                                showReleaseTitle
                                showInformation
                              />
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
});

export default AddSingleListen;
