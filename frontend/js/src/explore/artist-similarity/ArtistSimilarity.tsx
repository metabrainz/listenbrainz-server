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
import { isEqual } from "lodash";
import { ToastMsg } from "../../notifications/Notifications";
import { getPageProps } from "../../utils/utils";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SearchBox from "./artist-search/SearchBox";
import SimilarArtistsGraph from "./SimilarArtistsGraph";
import Panel from "./artist-panel/Panel";
import BrainzPlayer from "../../common/brainzplayer/BrainzPlayer";
import generateTransformedArtists from "./generateTransformedArtists";
import { downloadComponentAsImage, copyImageToClipboard } from "./utils";

type ArtistSimilarityProps = {
  algorithm: string;
  artist_mbid: string;
};

const SIMILAR_ARTISTS_LIMIT_VALUE = 18;
const BACKGROUND_ALPHA = 0.2;
const MAXIMUM_LUMINANCE = 0.8;
const MINIMUM_LUMINANCE = 0.2;

const colorGenerator = (): [tinycolor.Instance, tinycolor.Instance] => {
  const initialColor = tinycolor(`hsv(${Math.random() * 360}, 100%, 90%)`);
  return [initialColor, initialColor.clone().tetrad()[1]];
};
const isColorTooLight = (color: tinycolor.Instance): boolean => {
  return color.getLuminance() > MAXIMUM_LUMINANCE;
};
const isColorTooDark = (color: tinycolor.Instance): boolean => {
  return color.getLuminance() < MINIMUM_LUMINANCE;
};

function ArtistSimilarity(props: ArtistSimilarityProps) {
  const {
    algorithm: DEFAULT_ALGORITHM,
    artist_mbid: DEFAULT_ARTIST_MBID,
  } = props;

  const BASE_URL = `https://labs.api.listenbrainz.org/similar-artists/json?algorithm=${DEFAULT_ALGORITHM}&artist_mbid=`;
  const DEFAULT_COLORS = colorGenerator();

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

  const [colors, setColors] = React.useState(DEFAULT_COLORS);
  const [loading, setLoading] = React.useState<boolean>(false);

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

        setArtistGraphNodeInfo(data[1]?.data[0] ?? null);
        const similarArtists = data[3]?.data ?? [];

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

  const transformedArtists = React.useMemo(
    () =>
      artistGraphNodeInfo
        ? generateTransformedArtists(
            artistGraphNodeInfo,
            similarArtistsList,
            colors[0],
            colors[1],
            similarArtistsLimit
          )
        : {
            nodes: [],
            links: [],
          },
    [artistGraphNodeInfo, similarArtistsList, colors, similarArtistsLimit]
  );

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
        mbLink: `https://musicbrainz.org/artist/${artistMBID}`,
        topTracks: topRecordingsForArtist ?? null,
        topAlbum: topAlbumsForArtist?.[0] ?? null,
        artist_mbid: artistInformation[0]?.artist_mbid,
        gender: artistInformation[0]?.gender,
      };
      setArtistInfo(newArtistInfo);

      const topAlbumReleaseColor = topAlbumsForArtist[0]?.release_color;
      const topRecordingReleaseColor = topRecordingsForArtist[0]?.release_color;
      let firstColor;
      let secondColor;
      if (topAlbumReleaseColor) {
        const { red, green, blue } = topAlbumReleaseColor;
        firstColor = tinycolor({ r: red, g: green, b: blue });
      } else {
        // Do we want to pick a color from an array of predefined colors instead of random?
        firstColor = tinycolor.random();
      }
      if (topRecordingReleaseColor) {
        const { red, green, blue } = topRecordingReleaseColor;
        secondColor = tinycolor({ r: red, g: green, b: blue });
      } else {
        // If we don't have required release info, base the second color on the first,
        // randomly picking one of the tetrad complementary colors.
        const randomTetradColor = Math.round(Math.random() * (3 - 1) + 1);
        secondColor = tinycolor(firstColor).clone().tetrad()[randomTetradColor];
      }

      // Adjust the colors if they are too light or too dark
      [firstColor, secondColor].forEach((color) => {
        if (isColorTooLight(color)) {
          color.darken(30).saturate(15);
        } else if (isColorTooDark(color)) {
          color.lighten(30).saturate(15);
        }
      });

      setColors([firstColor, secondColor]);

      return newArtistInfo;
    },
    [APIService]
  );

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
        setLoading(true);
        const [newArtistInfo, _] = await Promise.all([
          fetchArtistInfo(artistMBID),
          fetchArtistSimilarityInfo(artistMBID),
        ]);
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
        {artistInfo && <Panel artistInfo={artistInfo} loading={loading} />}
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

document.addEventListener("DOMContentLoaded", async () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
  } = await getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }

  const { algorithm, artist_mbid } = reactProps;

  const ArtistSimilarityPageWithAlertNotifications = withAlertNotifications(
    ArtistSimilarity
  );

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <ArtistSimilarityPageWithAlertNotifications
            algorithm={algorithm}
            artist_mbid={artist_mbid}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
