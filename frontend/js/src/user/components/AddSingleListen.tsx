import React, { useEffect, useState } from "react";
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
  onPayloadChange: (
    recording?: MusicBrainzRecordingWithReleases,
    release?: MusicBrainzRelease
  ) => void;
}

export default function AddSingleListen({
  onPayloadChange,
}: AddSingleListenProps) {
  const [selectedRecording, setSelectedRecording] = useState<
    MusicBrainzRecordingWithReleases
  >();
  const [selectedRelease, setSelectedRelease] = useState<MusicBrainzRelease>();

  const resetTrackSelection = () => {
    setSelectedRecording(undefined);
    setSelectedRelease(undefined);
  };
  const listenFromSelectedRecording = React.useMemo(() => {
    return (
      selectedRecording &&
      getListenFromRecording(selectedRecording, new Date(), selectedRelease)
    );
  }, [selectedRecording, selectedRelease]);

  useEffect(() => {
    if (selectedRecording) {
      onPayloadChange(selectedRecording, selectedRelease);
    } else {
      onPayloadChange(undefined, undefined);
    }
  }, [selectedRecording, selectedRelease, onPayloadChange]);

  return (
    <div>
      <SearchTrackOrMBID
        expectedPayload="recording"
        onSelectRecording={(newSelectedRecording) => {
          setSelectedRecording(newSelectedRecording);
          if (newSelectedRecording.releases?.length === 1) {
            setSelectedRelease(newSelectedRecording.releases[0]);
          } else {
            setSelectedRelease(undefined);
          }
        }}
      />
      <div className="track-info">
        <div className="content">
          {listenFromSelectedRecording && (
            <ListenCard
              listen={listenFromSelectedRecording}
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
                  action={resetTrackSelection}
                />
              }
            />
          )}
        </div>
      </div>
      {selectedRecording && selectedRecording?.releases?.length > 1 && (
        <>
          <h5
            data-toggle="collapse"
            data-target="#select-release-collapsible"
            aria-controls="select-release-collapsible"
            className="header-with-line"
            style={{
              gap: "5px",
              marginBottom: "0.5em",
              alignItems: "baseline",
              cursor: "pointer",
            }}
          >
            Choose from {selectedRecording?.releases?.length} releases{" "}
            <small>(optional)</small>{" "}
            <FontAwesomeIcon icon={faChevronDown} size="sm" />
          </h5>
          <div className="collapse" id="select-release-collapsible">
            <div className="release-cards-grid">
              {selectedRecording.releases.map((release) => {
                return (
                  <span
                    data-toggle="collapse"
                    data-target="#select-release-collapsible"
                    key={release.id}
                  >
                    <ReleaseCard
                      onClick={() => {
                        setSelectedRelease(release);
                      }}
                      releaseName={release.title}
                      releaseDate={release.date}
                      dateFormatOptions={{ year: "numeric", month: "short" }}
                      releaseMBID={release.id}
                      artistCreditName={selectedRecording["artist-credit"]
                        ?.map((artist) => `${artist.name}${artist.joinphrase}`)
                        .join("")}
                      artistCredits={selectedRecording["artist-credit"].map(
                        (ac) => ({
                          artist_credit_name: ac.name,
                          artist_mbid: ac.artist.id,
                          join_phrase: ac.joinphrase,
                        })
                      )}
                      artistMBIDs={selectedRecording["artist-credit"]?.map(
                        (ac) => ac.artist.id
                      )}
                      releaseTypePrimary={
                        release.packaging === "None" ? null : release.packaging
                      }
                      caaID={null}
                      caaReleaseMBID={release.id}
                      showTags={false}
                      showArtist
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
}
