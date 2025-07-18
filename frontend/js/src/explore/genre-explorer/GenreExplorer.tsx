import * as React from "react";
import { faCopy, faDownload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useQuery } from "@tanstack/react-query";
import { kebabCase, merge } from "lodash";
import { Helmet } from "react-helmet";
import { useLocation, useNavigate, useParams } from "react-router";
import { toast } from "react-toastify";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";
import Loader from "../../components/Loader";
import { ToastMsg } from "../../notifications/Notifications";
import PlaylistItemCard from "../../playlists/components/PlaylistItemCard";
import {
  getRecordingMBIDFromJSPFTrack,
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
} from "../../playlists/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { RouteQuery } from "../../utils/Loader";
import {
  copyImageToClipboard,
  downloadComponentAsImage,
} from "../music-neighborhood/utils/utils";
import GenreGraph from "./components/GenreGraph";
import Panel from "./components/Panel";
import SearchBox from "./components/SearchBox";
import { transformGenreData } from "./utils/utils";

type LBRadioPlaylistResponse = {
  payload: {
    jspf: JSPFObject;
    feedback: string[];
  };
};

export default function GenreExplorer() {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams<GenreExplorerParams>();
  const graphParentElementRef = React.useRef<HTMLDivElement>(null);
  const { APIService } = React.useContext(GlobalAppContext);
  const dispatch = useBrainzPlayerDispatch();

  // Query for genre data
  const { data: genreData } = useQuery<GenreExplorerLoaderData>(
    RouteQuery(["genre-explorer", params], location.pathname)
  );

  const graphData = React.useMemo(() => transformGenreData(genreData!), [
    genreData,
  ]);

  // Query for playlist data
  const { data: playlistData, isLoading, error: playlistError } = useQuery({
    queryKey: ["genre-playlist", genreData?.genre?.name],
    queryFn: async () => {
      if (!genreData?.genre?.name) {
        return null;
      }

      const request = await fetch(
        `${APIService.APIBaseURI}/explore/lb-radio?prompt=${encodeURIComponent(
          `tag:(${genreData.genre.name})`
        )}&mode=easy`
      );

      if (!request.ok) {
        const errorData = await request.json();
        throw new Error(errorData?.error || "Failed to generate playlist");
      }

      const response = (await request.json()) as LBRadioPlaylistResponse;
      const { playlist } = response.payload.jspf;

      if (playlist?.track?.length) {
        try {
          const recordingMetadataMap = await APIService.getRecordingMetadata(
            playlist.track.map(getRecordingMBIDFromJSPFTrack)
          );

          if (recordingMetadataMap) {
            playlist.track.forEach((track) => {
              const mbid = getRecordingMBIDFromJSPFTrack(track);
              if (recordingMetadataMap[mbid]) {
                const newTrackObject = {
                  duration: recordingMetadataMap[mbid].recording?.length,
                  extension: {
                    [MUSICBRAINZ_JSPF_TRACK_EXTENSION]: {
                      additional_metadata: {
                        caa_id: recordingMetadataMap[mbid].release?.caa_id,
                        caa_release_mbid:
                          recordingMetadataMap[mbid].release?.caa_release_mbid,
                        artists: recordingMetadataMap[
                          mbid
                        ].artist?.artists?.map((a) => ({
                          artist_credit_name: a.name,
                          artist_mbid: a.artist_mbid,
                          join_phrase: a.join_phrase || "",
                        })),
                      },
                    },
                  },
                };
                merge(track, newTrackObject);
              }
            });
          }
        } catch (error) {
          // eslint-disable-next-line no-console
          console.error("Error fetching metadata:", error);
        }
      }

      return response;
    },
    enabled: Boolean(genreData?.genre?.name), // Only run query when we have a genre name
  });

  // Update BrainzPlayer queue when playlist data changes
  React.useEffect(() => {
    if (playlistData?.payload.jspf.playlist?.track) {
      dispatch({
        type: "SET_AMBIENT_QUEUE",
        data: playlistData.payload.jspf.playlist.track.map(JSPFTrackToListen),
      });
    }
  }, [playlistData, dispatch]);

  const handleGenreChange = (newGenreMBID: string) => {
    navigate(`/explore/genre-explorer/${newGenreMBID}/`);
  };

  const onClickDownload = React.useCallback(async () => {
    if (!graphParentElementRef?.current) {
      return;
    }

    try {
      downloadComponentAsImage(
        graphParentElementRef.current,
        `${kebabCase(genreData?.genre.name)}-genre-explorer.png`
      );
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not save as an image"
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "download-svg-error" }
      );
    }
  }, [genreData, graphParentElementRef]);

  const copyImage = React.useCallback(async () => {
    if (!graphParentElementRef?.current) {
      return;
    }

    await copyImageToClipboard(graphParentElementRef.current);
  }, [graphParentElementRef]);

  const browserHasClipboardAPI = "clipboard" in navigator;

  return (
    <>
      <Helmet>
        <title>Genre Explorer</title>
      </Helmet>
      <div className="genre-explorer-main-container" role="main">
        <div className="genre-explorer-header align-items-end">
          <SearchBox onGenreSelect={handleGenreChange} />
          <div>
            <button
              type="button"
              className="btn btn-icon btn-info"
              onClick={onClickDownload}
            >
              <FontAwesomeIcon icon={faDownload} color="white" />
            </button>
            {browserHasClipboardAPI && (
              <button
                type="button"
                className="btn btn-icon btn-info"
                onClick={copyImage}
              >
                <FontAwesomeIcon icon={faCopy} color="white" />
              </button>
            )}
          </div>
        </div>
        <div className="genre-explorer-content">
          <GenreGraph
            data={graphData}
            onGenreChange={handleGenreChange}
            graphParentElementRef={graphParentElementRef}
          />
          <Panel genre={genreData?.genre ?? null} />
        </div>
        <Loader
          isLoading={isLoading}
          loaderText="Generating playlist…"
          className="playlist-loader"
        >
          {playlistError && (
            <div className="alert alert-danger">
              Error generating playlist: {playlistError.message}
            </div>
          )}
          {playlistData?.payload.jspf.playlist && (
            <div className="genre-playlist">
              <h3>Generated Playlist</h3>
              {playlistData.payload.jspf.playlist.track.map(
                (track: JSPFTrack, index: number) => {
                  return (
                    <PlaylistItemCard
                      key={`${track.id}-${index.toString()}`}
                      canEdit={false}
                      track={track}
                    />
                  );
                }
              )}
            </div>
          )}
        </Loader>
      </div>
    </>
  );
}
