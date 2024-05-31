import React, { useContext, useEffect, useState } from "react";
import { toast } from "react-toastify";
import { sortBy, without } from "lodash";
import SearchAlbumOrMBID from "../../utils/SearchAlbumOrMBID";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { millisecondsToStr } from "../../playlists/utils";

interface AddAlbumListensProps {
  onPayloadChange: (tracks: Array<MusicBrainzTrackWithArtistCredits>) => void;
}

type MusicBrainzTrackWithArtistCredits = MusicBrainzTrack & WithArtistCredits;

type MBReleaseWithMetadata = MusicBrainzRelease &
  WithMedia &
  WithArtistCredits &
  WithReleaseGroup;

type TrackRowProps = {
  track: MusicBrainzTrackWithArtistCredits;
  isChecked: boolean;
  onClickCheckbox: (
    track: MusicBrainzTrackWithArtistCredits,
    checked: boolean
  ) => void;
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
      <strong className="small track-number">{track.position}</strong>
      <span>{track.title}</span>
      {track.length && (
        <span className="pull-right">{millisecondsToStr(track.length)}</span>
      )}
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
  const [selectedTracks, setSelectedTracks] = useState<
    Array<MusicBrainzTrackWithArtistCredits>
  >([]);

  useEffect(() => {
    // Update parent on selection change
    onPayloadChange(selectedTracks);
  }, [selectedTracks, onPayloadChange]);

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
          .map(({ tracks }) => tracks as MusicBrainzTrackWithArtistCredits[])
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
    (track: MusicBrainzTrackWithArtistCredits, isChecked: boolean) => {
      setSelectedTracks((prevSelectedTracks) => {
        let newSelection: MusicBrainzTrackWithArtistCredits[];
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
                    return (
                      <div key={medium.format + medium.position + medium.title}>
                        {selectedAlbum.media.length > 1 && (
                          <div>
                            {medium.format}&nbsp;
                            {medium.position}
                            {medium.title && ` - ${medium.title}`}
                          </div>
                        )}
                        {medium?.tracks?.map((track) => {
                          return (
                            <TrackRow
                              key={track.id}
                              track={track as MusicBrainzTrackWithArtistCredits}
                              onClickCheckbox={onTrackSelectionChange}
                              isChecked={selectedTracks.includes(
                                track as MusicBrainzTrackWithArtistCredits
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
