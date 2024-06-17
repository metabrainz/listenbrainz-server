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
    recording?: MusicBrainzRecordingWithReleasesAndRGs,
    release?: MusicBrainzRelease & WithReleaseGroup
  ) => void;
}

export default function AddSingleListen({
  onPayloadChange,
}: AddSingleListenProps) {
  const [selectedRecording, setSelectedRecording] = useState<
    MusicBrainzRecordingWithReleasesAndRGs
  >();
  const [selectedRelease, setSelectedRelease] = useState<
    MusicBrainzRelease & WithReleaseGroup
  >();

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
            className="header-with-line collapsed"
            style={{
              gap: "5px",
              marginBottom: "0.5em",
              alignItems: "center",
              cursor: "pointer",
            }}
            id="select-release"
          >
            Choose from {selectedRecording?.releases?.length} releases&nbsp;
            <small>(optional)</small>&nbsp;
            <FontAwesomeIcon icon={faChevronDown} size="xs" />
          </h5>
          <div className="collapse" id="select-release-collapsible">
            <div className="help-block">
              Too many choices? See more details{" "}
              <a
                href={`https://musicbrainz.org/recording/${selectedRecording.id}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                on MusicBrainz
              </a>
              .
            </div>
            <div className="release-cards-grid">
              {selectedRecording.releases.map((release) => {
                const releaseGroup = release["release-group"];
                return (
                  <span
                    data-toggle="collapse"
                    data-target="#select-release-collapsible"
                    key={release.id}
                  >
                    <ReleaseCard
                      key={release.id}
                      onClick={() => {
                        setSelectedRelease(release);
                      }}
                      releaseName={release.title}
                      releaseDate={release.date}
                      dateFormatOptions={{ year: "numeric", month: "short" }}
                      releaseMBID={release.id}
                      releaseGroupMBID={releaseGroup?.id}
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
                      releaseTypePrimary={releaseGroup?.["primary-type"]}
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
}
