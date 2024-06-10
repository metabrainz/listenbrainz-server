import React, { useContext, useEffect, useState } from "react";
import { toast } from "react-toastify";
import { differenceBy, padStart, sortBy, uniqBy, without } from "lodash";
import SearchAlbumOrMBID from "../../utils/SearchAlbumOrMBID";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { millisecondsToStr } from "../../playlists/utils";
import { MBTrackWithAC } from "./AddListenModal";

interface AddAlbumListensProps {
  onPayloadChange: (
    tracks: Array<MBTrackWithAC>,
    release?: MusicBrainzRelease & WithReleaseGroup
  ) => void;
}

type MBReleaseWithMetadata = MusicBrainzRelease &
  WithMedia &
  WithArtistCredits &
  WithReleaseGroup;

type TrackRowProps = {
  track: MBTrackWithAC;
  isChecked: boolean;
  onClickCheckbox: (track: MBTrackWithAC, checked: boolean) => void;
};

function TrackRow({ track, isChecked, onClickCheckbox }: TrackRowProps) {
  return (
    <div className="add-album-track">
      <input
        type="checkbox"
        onChange={(e) => {
          onClickCheckbox(track, e.target.checked);
        }}
        checked={isChecked}
      />
      <strong className="small track-number">
        {padStart(track.position.toString(), 2, "0")}
      </strong>
      <span>{track.title}</span>
      <span className="duration">
        {track.length ? (
          millisecondsToStr(track.length)
        ) : (
          <span title="No track duration available; listen will be submitted with a default duration of 4 minutes">
            ?
          </span>
        )}
      </span>
    </div>
  );
}

export default function AddAlbumListens({
  onPayloadChange,
}: AddAlbumListensProps) {
  const { APIService } = useContext(GlobalAppContext);
  const { lookupMBRelease } = APIService;
  const [selectedAlbumMBID, setSelectedAlbumMBID] = useState<string>();
  const [selectedAlbum, setSelectedAlbum] = useState<MBReleaseWithMetadata>();
  const [selectedTracks, setSelectedTracks] = useState<Array<MBTrackWithAC>>(
    []
  );

  useEffect(() => {
    // Update parent on selection change
    onPayloadChange(selectedTracks, selectedAlbum);
  }, [selectedTracks, selectedAlbum, onPayloadChange]);

  const artistsName = selectedAlbum?.["artist-credit"]
    ?.map((artist) => `${artist.name}${artist.joinphrase}`)
    .join("");

  useEffect(() => {
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
        setSelectedTracks(newSelection);
      } catch (error) {
        toast.error(`Could not load track list for ${releaseMBID}`);
      }
    }
    if (!selectedAlbumMBID) {
      setSelectedAlbum(undefined);
      setSelectedTracks([]);
    } else {
      fetchTrackList(selectedAlbumMBID);
    }
  }, [selectedAlbumMBID, lookupMBRelease]);

  const onTrackSelectionChange = React.useCallback(
    (track: MBTrackWithAC, isChecked: boolean) => {
      setSelectedTracks((prevSelectedTracks) => {
        let newSelection: MBTrackWithAC[];
        if (isChecked) {
          newSelection = sortBy([...prevSelectedTracks, track], "position");
        } else {
          newSelection = without(prevSelectedTracks, track);
        }
        return newSelection;
      });
    },
    []
  );

  const toggleSelectionAllMediumTracks = React.useCallback(
    (tracks: MBTrackWithAC[], isChecked: boolean) => {
      setSelectedTracks((prevSelectedTracks) => {
        let newSelection: MBTrackWithAC[];
        if (isChecked) {
          const dedupedSelection = uniqBy(
            [...prevSelectedTracks, ...tracks],
            "id"
          );
          newSelection = sortBy(dedupedSelection, "position");
        } else {
          newSelection = without(prevSelectedTracks, ...tracks);
        }
        return newSelection;
      });
    },
    []
  );

  return (
    <div>
      <SearchAlbumOrMBID
        onSelectAlbum={(newSelectedAlbumId?: string) => {
          setSelectedAlbumMBID(newSelectedAlbumId);
        }}
      />
      <div className="track-info">
        {selectedAlbum && (
          <>
            <div
              className="header-with-line"
              style={{
                gap: "5px",
                marginBottom: "0.5em",
                alignItems: "baseline",
              }}
            >
              <strong>{selectedAlbum.title}</strong>
              {selectedAlbum.date && (
                <span>
                  &nbsp;({new Date(selectedAlbum.date).getFullYear()})
                </span>
              )}
              &nbsp;–&nbsp;{artistsName}
              {selectedAlbum["release-group"]?.["primary-type"] && (
                <small>
                  &nbsp;({selectedAlbum["release-group"]?.["primary-type"]})
                </small>
              )}
            </div>
            <div className="content">
              {selectedAlbum?.media.length &&
                selectedAlbum.media
                  .map((medium, index) => {
                    const allMediumTracksSelected =
                      differenceBy(medium.tracks, selectedTracks, "id")
                        .length === 0;
                    return (
                      <div key={medium.format + medium.position + medium.title}>
                        {selectedAlbum.media.length > 1 && (
                          <div className="add-album-track">
                            <input
                              type="checkbox"
                              onChange={(e) => {
                                toggleSelectionAllMediumTracks(
                                  medium.tracks as MBTrackWithAC[],
                                  e.target.checked
                                );
                              }}
                              title="select/deselect all tracks from this medium"
                              checked={allMediumTracksSelected}
                            />
                            <span className="badge badge-info">
                              {medium.format}&nbsp;
                              {medium.position}
                              {medium.title && ` - ${medium.title}`}
                            </span>
                          </div>
                        )}
                        {medium?.tracks?.map((track) => {
                          return (
                            <TrackRow
                              key={track.id}
                              track={track as MBTrackWithAC}
                              onClickCheckbox={onTrackSelectionChange}
                              isChecked={selectedTracks.includes(
                                track as MBTrackWithAC
                              )}
                            />
                          );
                        })}
                        {index >= 0 &&
                          index < selectedAlbum.media.length - 1 && <hr />}
                      </div>
                    );
                  })
                  .flat()}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
