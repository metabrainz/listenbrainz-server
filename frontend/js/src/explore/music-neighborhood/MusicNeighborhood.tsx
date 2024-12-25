import * as React from "react";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy, faDownload } from "@fortawesome/free-solid-svg-icons";
import { kebabCase } from "lodash";
import { useLocation } from "react-router-dom";
import { Helmet } from "react-helmet";
import { useQuery } from "@tanstack/react-query";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SearchBox from "./components/SearchBox";
import Panel from "./components/Panel";
import { downloadComponentAsImage, copyImageToClipboard } from "./utils/utils";
import { RouteQuery } from "../../utils/Loader";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";
import SimilarArtist from "./components/SimilarArtist";

type MusicNeighborhoodLoaderData = {
  algorithm: string;
  artist_mbid: string;
};

const SIMILAR_ARTISTS_LIMIT_VALUE = 18;

export default function MusicNeighborhood() {
  const location = useLocation();
  const { data } = useQuery<MusicNeighborhoodLoaderData>(
    RouteQuery(["music-neighborhood"], location.pathname)
  );
  const { algorithm: DEFAULT_ALGORITHM, artist_mbid: DEFAULT_ARTIST_MBID } =
    data || {};
  const BASE_URL = `https://labs.api.listenbrainz.org/similar-artists/json?algorithm=${DEFAULT_ALGORITHM}&artist_mbids=`;

  const { APIService } = React.useContext(GlobalAppContext);
  const [similarArtistsLimit, setSimilarArtistsLimit] = React.useState(
    SIMILAR_ARTISTS_LIMIT_VALUE
  );

  const [similarArtistsList, setSimilarArtistsList] = React.useState<
    Array<ArtistNodeInfo>
  >([]);
  const [
    completeSimilarArtistsList,
    setCompleteSimilarArtistsList,
  ] = React.useState<Array<ArtistNodeInfo>>([]);

  const [artistGraphNodeInfo, setArtistGraphNodeInfo] = React.useState<
    ArtistNodeInfo
  >();
  const [topAlbumReleaseColor, setTopAlbumReleaseColor] = React.useState<
    ReleaseColor
  >();
  const [
    topRecordingReleaseColor,
    setTopRecordingReleaseColor,
  ] = React.useState<ReleaseColor>();

  const [loading, setLoading] = React.useState<boolean>(false);

  const [currentTracks, setCurrentTracks] = React.useState<Array<Listen>>([]);

  const dispatch = useBrainzPlayerDispatch();

  React.useEffect(() => {
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: currentTracks,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTracks]);

  const [artistInfo, setArtistInfo] = React.useState<ArtistInfoType | null>(
    null
  );
  const artistInfoRef = React.useRef<ArtistInfoType | null>(null);
  artistInfoRef.current = artistInfo;

  const graphParentElementRef = React.useRef<HTMLDivElement>(null);

  const onClickDownload = React.useCallback(async () => {
    if (!graphParentElementRef?.current) {
      return;
    }

    try {
      downloadComponentAsImage(
        graphParentElementRef.current,
        `${kebabCase(artistInfo?.name)}-music-neighborhood.png`
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
  }, [artistInfo, graphParentElementRef]);

  const copyImage = React.useCallback(async () => {
    if (!graphParentElementRef?.current) {
      return;
    }

    await copyImageToClipboard(graphParentElementRef.current);
  }, [graphParentElementRef]);

  const fetchArtistSimilarityInfo = React.useCallback(
    async (artistMBID: string) => {
      try {
        const response = await fetch(BASE_URL + artistMBID);
        const artistSimilarityData = await response.json();

        if (!artistSimilarityData || !artistSimilarityData.length) {
          throw new Error("No Similar Artists Found");
        }

        const currentArtistName = artistInfoRef.current?.name;
        setArtistGraphNodeInfo({
          artist_mbid: artistMBID,
          name: currentArtistName ?? "Unknown",
        });
        const similarArtists = artistSimilarityData ?? [];

        setCompleteSimilarArtistsList(similarArtists);
        setSimilarArtistsList(similarArtists?.slice(0, similarArtistsLimit));
      } catch (error) {
        setSimilarArtistsList([]);
        toast.error(
          <ToastMsg
            title="Search Error"
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "error" }
        );
      }
    },
    [similarArtistsLimit, BASE_URL]
  );

  const updateSimilarArtistsLimit = (limit: number) => {
    setSimilarArtistsLimit(limit);
    setSimilarArtistsList(completeSimilarArtistsList.slice(0, limit));
  };

  const fetchArtistInfo = React.useCallback(
    async (artistMBID: string): Promise<ArtistInfoType> => {
      const [
        artistInformation,
        wikipediaData,
        topRecordingsForArtist,
        topAlbumsForArtist,
      ]: [
        Array<MusicBrainzArtist>,
        string,
        Array<RecordingType>,
        Array<ReleaseGroupType>
      ] = await Promise.all([
        APIService.lookupMBArtist(artistMBID, ""),
        APIService.getArtistWikipediaExtract(artistMBID),
        APIService.getTopRecordingsForArtist(artistMBID),
        APIService.getTopReleaseGroupsForArtist(artistMBID),
      ]);

      const birthAreaData = {
        born: artistInformation[0]?.begin_year || "Unknown",
        area: artistInformation[0]?.area || "Unknown",
      };

      const newArtistInfo: ArtistInfoType = {
        name: artistInformation[0]?.name,
        type: artistInformation[0]?.type,
        ...birthAreaData,
        wiki: wikipediaData,
        link: `/artist/${artistMBID}`,
        topTracks: topRecordingsForArtist ?? null,
        topAlbum: topAlbumsForArtist?.[0] ?? null,
        artist_mbid: artistInformation[0]?.artist_mbid,
        gender: artistInformation[0]?.gender,
      };
      setArtistInfo(newArtistInfo);

      setTopAlbumReleaseColor(topAlbumsForArtist[0]?.release_color ?? null);
      setTopRecordingReleaseColor(
        topRecordingsForArtist[0]?.release_color ?? null
      );

      return newArtistInfo;
    },
    [APIService]
  );

  const onArtistChange = React.useCallback(
    async (artistMBID: string) => {
      try {
        setLoading(true);
        const newArtistInfo = await fetchArtistInfo(artistMBID);
        await fetchArtistSimilarityInfo(artistMBID);
        setLoading(false);
        const topTracksAsListen = newArtistInfo?.topTracks?.map((topTrack) => ({
          listened_at: 0,
          track_metadata: {
            artist_name: topTrack.artist_name,
            track_name: topTrack.recording_name,
            release_name: topTrack.release_name,
            release_mbid: topTrack.release_mbid,
            recording_mbid: topTrack.recording_mbid,
          },
        }));
        setCurrentTracks(topTracksAsListen ?? []);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Search Error"
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "error" }
        );
      }
    },
    [fetchArtistSimilarityInfo, fetchArtistInfo]
  );

  React.useEffect(() => {
    if (DEFAULT_ARTIST_MBID) onArtistChange(DEFAULT_ARTIST_MBID);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const browserHasClipboardAPI = "clipboard" in navigator;

  return (
    <>
      <Helmet>
        <title>Music Neighborhood</title>
      </Helmet>
      <div className="artist-similarity-main-container" role="main">
        <div className="artist-similarity-header">
          <SearchBox
            onArtistChange={onArtistChange}
            onSimilarArtistsLimitChange={updateSimilarArtistsLimit}
            currentSimilarArtistsLimit={similarArtistsLimit}
          />
          <div className="share-buttons">
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
        <div className="artist-similarity-graph-panel-container">
          <SimilarArtist
            onArtistChange={onArtistChange}
            artistGraphNodeInfo={artistGraphNodeInfo}
            similarArtistsList={similarArtistsList}
            topAlbumReleaseColor={topAlbumReleaseColor}
            topRecordingReleaseColor={topRecordingReleaseColor}
            similarArtistsLimit={similarArtistsLimit}
            graphParentElementRef={graphParentElementRef}
          />
          {artistInfo && <Panel artistInfo={artistInfo} loading={loading} />}
        </div>
      </div>
    </>
  );
}
