import * as React from "react";
import NiceModal from "@ebay/nice-modal-react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import { ErrorBoundary } from "@sentry/react";
import tinycolor from "tinycolor2";
import { toast } from "react-toastify";
import { ToastMsg } from "../../notifications/Notifications";
import { getPageProps } from "../../utils/utils";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SearchBox from "./artist-search/SearchBox";
import SimilarArtistsGraph from "./SimilarArtistsGraph";
import Panel from "./artist-panel/Panel";
import BrainzPlayer from "../../brainzplayer/BrainzPlayer";
import generateTransformedArtists from "./generateTransformedArtists";

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

  const [colors, setColors] = React.useState(colorGenerator);
  const [artistInfo, setArtistInfo] = React.useState<ArtistType>();

  // Will Figure out how to use this later
  const [currentTracks, setCurrentTracks] = React.useState<Array<Listen>>();

  const onArtistChange = async (artistMBID: string) => {
    try {
      const response = await fetch(BASE_URL + artistMBID);
      const data = await response.json();

      if (!data || !data.length || data.length === 3) {
        throw new Error("No Similar Artists Found");
      }

      const mainArtist = data[1]?.data[0];
      const similarArtists = data[3]?.data ?? [];

      setArtistInfo(mainArtist);
      setCompleteSimilarArtistsList(similarArtists);
      setSimilarArtistsList(similarArtists?.slice(0, similarArtistsLimit));

      // Set the background color of the graph
      setColors((prevColors) => [prevColors[1], prevColors[1].tetrad()[1]]);
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
  };

  const updateSimilarArtistsLimit = (limit: number) => {
    setSimilarArtistsLimit(limit);
    setSimilarArtistsList(completeSimilarArtistsList.slice(0, limit));
  };

  const transformedArtists = React.useMemo(
    () =>
      artistInfo
        ? generateTransformedArtists(
            artistInfo,
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

  const backgroundGradient = React.useMemo(() => {
    const color1 = colors[0].clone().setAlpha(BACKGROUND_ALPHA).toRgbString();
    const color2 = colors[1].clone().setAlpha(BACKGROUND_ALPHA).toRgbString();
    return `linear-gradient(90deg, ${color1} 0%, ${color2} 100%)`;
  }, [colors]);

  React.useEffect(() => {
    onArtistChange(DEFAULT_ARTIST_MBID);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="artist-similarity-main-container">
      <SearchBox
        onArtistChange={onArtistChange}
        onSimilarArtistsLimitChange={updateSimilarArtistsLimit}
        currentSimilarArtistsLimit={similarArtistsLimit}
      />
      <div className="artist-similarity-graph-panel-container">
        <SimilarArtistsGraph
          onArtistChange={onArtistChange}
          data={transformedArtists}
          background={backgroundGradient}
        />
        {artistInfo && (
          <Panel artist={artistInfo} onTrackChange={setCurrentTracks} />
        )}
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
