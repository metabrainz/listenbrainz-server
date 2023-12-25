import * as React from "react";
import NiceModal from "@ebay/nice-modal-react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { ErrorBoundary } from "@sentry/react";
import tinycolor from "tinycolor2";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy, faDownload } from "@fortawesome/free-solid-svg-icons";
import { ToastMsg } from "../../notifications/Notifications";
import { getPageProps } from "../../utils/utils";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SearchBox from "./artist-search/SearchBox";
import SimilarArtistsGraph from "./SimilarArtistsGraph";
import Panel from "./artist-panel/Panel";
import BrainzPlayer from "../../brainzplayer/BrainzPlayer";
import generateTransformedArtists from "./generateTransformedArtists";
import { downloadComponentAsImage, copyImageToClipboard } from "./utils";

const DEFAULT_ARTIST_MBID = "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11";
const SIMILAR_ARTISTS_LIMIT_VALUE = 18;
const BASE_URL =
  "https://labs.api.listenbrainz.org/similar-artists/json?algorithm=session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30&artist_mbid=";
// Apha value of the background color of the graph
const BACKGROUND_ALPHA = 0.2;

const colorGenerator = (): [tinycolor.Instance, tinycolor.Instance] => {
  const initialColor = tinycolor(`hsv(${Math.random() * 360}, 100%, 90%)`);
  return [initialColor, initialColor.clone().tetrad()[1]];
};

function ArtistSimilarity() {
  const { APIService } = React.useContext(GlobalAppContext);
  const [similarArtistsLimit, setSimilarArtistsLimit] = React.useState(
    SIMILAR_ARTISTS_LIMIT_VALUE
  );

  const [similarArtistsList, setSimilarArtistsList] = React.useState<
    Array<ArtistType>
  >([]);
  const [
    completeSimilarArtistsList,
    setCompleteSimilarArtistsList,
  ] = React.useState<Array<ArtistType>>([]);

  const [colors, setColors] = React.useState([
    tinycolor("#FF87AE"),
    tinycolor("#001616"),
  ]);
  const [currentTracks, setCurrentTracks] = React.useState<Array<Listen>>([]);

  const [artistInfo, setArtistInfo] = React.useState<ArtistInfoType | null>(
    null
  );

  const graphParentElementRef = React.useRef<HTMLDivElement>(null);

  const onClickDownload = React.useCallback(async () => {
    if (!graphParentElementRef?.current) {
      return;
    }

    try {
      downloadComponentAsImage(
        graphParentElementRef.current,
        `${artistInfo?.name}-similarity-graph.png`
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
        const data = await response.json();

        if (!data || !data.length || data.length === 3) {
          throw new Error("No Similar Artists Found");
        }

        const similarArtists = data[3]?.data ?? [];

        setCompleteSimilarArtistsList(similarArtists);
        setSimilarArtistsList(similarArtists?.slice(0, similarArtistsLimit));

        // Set the background color of the graph
        // setColors((prevColors) => [prevColors[1], prevColors[1].tetrad()[1]]);
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
    [similarArtistsLimit]
  );

  const updateSimilarArtistsLimit = (limit: number) => {
    setSimilarArtistsLimit(limit);
    setSimilarArtistsList(completeSimilarArtistsList.slice(0, limit));
  };

  const transformedArtists = React.useMemo(
    () =>
      artistInfo
        ? generateTransformedArtists(
            {
              artist_mbid: artistInfo.artist_mbid,
              name: artistInfo.name,
              type: artistInfo.type,
              gender: artistInfo.gender,
            },
            similarArtistsList,
            colors[0],
            colors[1],
            similarArtistsLimit
          )
        : {
            nodes: [],
            links: [],
          },
    [artistInfo, similarArtistsList, colors, similarArtistsLimit]
  );

  const fetchArtistInfo = React.useCallback(async (artistMBID: string): Promise<
    ArtistInfoType
  > => {
    const [
      artistInformation,
      wikipediaData,
      topRecordingsForArtist,
      topAlbumsForArtist,
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

    const newArtistInfo = {
      name: artistInformation[0]?.name,
      type: artistInformation[0]?.type,
      ...birthAreaData,
      wiki: wikipediaData,
      mbLink: `https://musicbrainz.org/artist/${artistMBID}`,
      topTracks: topRecordingsForArtist ?? null,
      topAlbum: topAlbumsForArtist?.[0] ?? null,
      artist_mbid: artistInformation[0]?.artist_mbid,
      gender: artistInformation[0]?.gender,
    };
    setArtistInfo(newArtistInfo);
    return newArtistInfo;
  }, []);

  const backgroundGradient = React.useMemo(() => {
    const releaseHue = colors[0]
      .clone()
      .setAlpha(BACKGROUND_ALPHA)
      .toRgbString();
    const recordingHue = colors[1]
      .clone()
      .setAlpha(BACKGROUND_ALPHA)
      .toRgbString();
    return `linear-gradient(180deg, ${releaseHue} 0%, ${recordingHue} 100%)`;
  }, [colors]);

  const onArtistChange = React.useCallback(
    async (artistMBID: string) => {
      try {
        const [_, newArtistInfo] = await Promise.all([
          fetchArtistSimilarityInfo(artistMBID),
          fetchArtistInfo(artistMBID),
        ]);
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
    onArtistChange(DEFAULT_ARTIST_MBID);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const browserHasClipboardAPI = "clipboard" in navigator;

  return (
    <div className="artist-similarity-main-container">
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
        <SimilarArtistsGraph
          onArtistChange={onArtistChange}
          data={transformedArtists}
          background={backgroundGradient}
          graphParentElementRef={graphParentElementRef}
        />
        {artistInfo && <Panel artistInfo={artistInfo} />}
      </div>
      <BrainzPlayer
        listens={currentTracks ?? []}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
        refreshSoundcloudToken={APIService.refreshSoundcloudToken}
      />
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, globalAppContext, sentryProps } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const ArtistSimilarityPageWithAlertNotifications = withAlertNotifications(
    ArtistSimilarity
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <ArtistSimilarityPageWithAlertNotifications />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
