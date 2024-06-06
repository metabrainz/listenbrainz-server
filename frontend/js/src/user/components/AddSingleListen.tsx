import React, { useEffect, useState } from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
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
  };
  const listenFromSelectedRecording =
    selectedRecording && getListenFromRecording(selectedRecording);

  useEffect(() => {
    if (selectedRecording) {
      onPayloadChange(selectedRecording, selectedRelease);
    } else {
      onPayloadChange(undefined);
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
      {!selectedRelease &&
        selectedRecording &&
        selectedRecording?.releases?.length > 1 && (
          <>
            <h4>
              Choose a release <small>(optional)</small>
            </h4>
            <br />
            <div>
              {selectedRecording.releases.map((release) => {
                return (
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
                );
              })}
            </div>
          </>
        )}
    </div>
  );
}
