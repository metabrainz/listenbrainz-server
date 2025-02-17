import React, {
  ChangeEvent,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { toast } from "react-toastify";
import {
  differenceBy,
  identity,
  isFinite,
  padStart,
  sortBy,
  uniq,
  uniqBy,
  without,
} from "lodash";
import { formatDuration, isValid } from "date-fns";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faClock } from "@fortawesome/free-regular-svg-icons";
import SearchAlbumOrMBID from "../../utils/SearchAlbumOrMBID";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { millisecondsToStr } from "../../playlists/utils";
import {
  DEFAULT_TRACK_LENGTH_SECONDS,
  MBTrackWithAC,
  getListenFromTrack,
} from "./AddListenModal";

interface AddAlbumListensProps {
  onPayloadChange: (listens: Listen[]) => void;
  switchMode: (text: string) => void;
  initialText?: string;
}

export type MBReleaseWithMetadata = MusicBrainzRelease &
  WithMedia &
  WithArtistCredits &
  WithReleaseGroup;

/* Allows sorting a selection of tracks based on the original order of that track in the multiple media
  We cannot just order by the position attribute because it is repeated for each medium (each medium will have a track 1).
  Courtesy of Shl for this elegant solution: https://stackoverflow.com/a/62298591/4904467
*/
function sortByArray<T, U>({
  source,
  by,
  sourceTransformer = identity,
}: {
  source: T[];
  by: U[];
  sourceTransformer?: (item: T) => U;
}) {
  const indexesByElements = new Map(by.map((item, idx) => [item, idx]));
  const orderedResult = sortBy(source, (p) =>
    indexesByElements.get(sourceTransformer(p))
  );
  return orderedResult;
}

type TrackRowProps = {
  track: MBTrackWithAC;
  isChecked: boolean;
  onClickCheckbox: (
    track: MBTrackWithAC,
    e: React.ChangeEvent<HTMLInputElement>
  ) => void;
};

export function TrackRow({ track, isChecked, onClickCheckbox }: TrackRowProps) {
  const trackDuration = track.length ?? track.recording.length;
  return (
    <div className="add-album-track">
      <input
        type="checkbox"
        onChange={(event) => {
          onClickCheckbox(track, event);
        }}
        checked={isChecked}
      />
      <strong className="small track-number">
        {isFinite(Number(track.number))
          ? padStart(track.position.toString(), 2, "0")
          : track.number}
      </strong>
      <span>{track.title}</span>
      <span className={`duration ${!trackDuration ? "default-duration" : ""}`}>
        {millisecondsToStr(
          trackDuration ?? DEFAULT_TRACK_LENGTH_SECONDS * 1000
        )}
      </span>
    </div>
  );
}

export default function AddAlbumListens({
  onPayloadChange,
  switchMode,
  initialText,
}: AddAlbumListensProps) {
  const { APIService } = useContext(GlobalAppContext);
  const { lookupMBRelease } = APIService;
  const [selectedAlbumMBID, setSelectedAlbumMBID] = useState<string>();
  const [selectedAlbum, setSelectedAlbum] = useState<MBReleaseWithMetadata>();
  const [selectedTracks, setSelectedTracks] = useState<Array<MBTrackWithAC>>(
    []
  );
  const searchInputRef = useRef<{
    focus(): void;
    triggerSearch(newText: string): void;
  }>(null);

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

  // No need to store that one in the state
  const lastChecked = useRef<MBTrackWithAC>();
  const allTracks: MBTrackWithAC[] = useMemo(
    () =>
      selectedAlbum?.media.map((m) => m.tracks as MBTrackWithAC[]).flat() ?? [],
    [selectedAlbum]
  );

  useEffect(() => {
    // Update parent on selection change
    const date = new Date();
    const listensFromTracks: Listen[] = selectedTracks.map((track) =>
      getListenFromTrack(track, date, selectedAlbum)
    );
    onPayloadChange(listensFromTracks);
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
    (track: MBTrackWithAC, event: ChangeEvent<HTMLInputElement>) => {
      setSelectedTracks((prevSelectedTracks) => {
        let newSelection: MBTrackWithAC[] = [];
        const isChecked = event.target.checked;
        // @ts-ignore nativeEvent.shiftKey exists for there input events,
        // but the react types define a very basic Event type which does not have shiftKey
        const shiftKey = Boolean(event.nativeEvent.shiftKey!);
        if (shiftKey && lastChecked?.current !== track) {
          const lastIndex = allTracks!.findIndex(
            (t) => t === lastChecked.current
          );
          const thisIndex = allTracks!.findIndex((t) => t === track);

          if (lastIndex > thisIndex) {
            const trackRange = allTracks!.slice(thisIndex, lastIndex + 1);
            newSelection = isChecked
              ? uniq([...trackRange, ...prevSelectedTracks])
              : without(prevSelectedTracks, ...trackRange);
          } else if (thisIndex > lastIndex) {
            const trackRange = allTracks!.slice(lastIndex, thisIndex + 1);
            newSelection = isChecked
              ? uniq([...prevSelectedTracks, ...trackRange])
              : without(prevSelectedTracks, ...trackRange);
          }
        } else if (isChecked) {
          newSelection = [...prevSelectedTracks, track];
        } else {
          newSelection = without(prevSelectedTracks, track);
        }
        lastChecked.current = track;
        // return sortBy(newSelection, mediumPosition, "position");
        // Sort according to the original order of the track, fix for multiple medium
        return sortByArray({
          source: newSelection,
          by: allTracks.map((t) => t.id),
          sourceTransformer: (t) => t.id,
        });
      });
    },
    [allTracks]
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

  const allDurations = selectedAlbum?.media.flatMap((medium) =>
    medium.tracks.map((track) => track.length ?? track.recording.length)
  );
  const showDefaultDuration = !allDurations?.every(Boolean);

  const defaultDuration = formatDuration(
    {
      seconds: DEFAULT_TRACK_LENGTH_SECONDS,
    },
    { format: ["minutes", "seconds"] }
  );

  return (
    <div>
      <SearchAlbumOrMBID
        onSelectAlbum={(newSelectedAlbumId?: string) => {
          setSelectedAlbumMBID(newSelectedAlbumId);
        }}
        switchMode={switchMode}
        ref={searchInputRef}
      />
      <div className="track-info">
        {selectedAlbum && (
          <>
            <div className="header-with-line">
              <a
                href={`https://musicbrainz.org/release/${selectedAlbum.id}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <strong>{selectedAlbum.title}</strong>
              </a>
              {selectedAlbum.date && isValid(new Date(selectedAlbum.date)) && (
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
            {showDefaultDuration && (
              <div
                className="default-duration heading small"
                title={`When no duration is available a default of ${defaultDuration} will be used`}
              >
                default {defaultDuration}
              </div>
            )}
            <div className="content">
              {selectedAlbum?.media.length &&
                selectedAlbum.media
                  .map((medium, index) => {
                    const allMediumTracksSelected =
                      differenceBy(medium.tracks, selectedTracks, "id")
                        .length === 0;
                    const mediumTime = medium.tracks
                      .map(
                        (track) =>
                          track.length ??
                          track.recording.length ??
                          DEFAULT_TRACK_LENGTH_SECONDS * 1000
                      )
                      ?.reduce((total, duration) => total + duration, 0);

                    return (
                      <div key={medium.format + medium.position + medium.title}>
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
                          <span className="small text-muted">
                            <FontAwesomeIcon icon={faClock} />{" "}
                            {millisecondsToStr(mediumTime)}
                          </span>
                        </div>
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
