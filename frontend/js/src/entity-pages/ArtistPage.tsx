import * as React from "react";
import { createRoot } from "react-dom/client";

import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import NiceModal from "@ebay/nice-modal-react";
import { toast, ToastContainer } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronLeft,
  faChevronRight,
  faHeadphones,
  faUserAstronaut,
} from "@fortawesome/free-solid-svg-icons";
import { sortBy } from "lodash";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import { getPageProps } from "../utils/utils";
import BrainzPlayer from "../brainzplayer/BrainzPlayer";
import { ToastMsg } from "../notifications/Notifications";
import TagsComponent from "../tags/TagsComponent";
import ReleaseCard from "../explore/fresh-releases/ReleaseCard";
import ListenCard from "../listens/ListenCard";

export type ArtistPageProps = {
  popular_tracks?: JSPFTrack[];
  artist_tags?: ArtistTag[];
  artist: MusicBrainzArtist;
};
const fakeArtist: MusicBrainzArtist = {
  area: "United Kingdom",
  begin_year: 1986,
  join_phrase: " feat. ",
  name: "Coldcut",
  rels: {
    "free streaming": "https://www.deezer.com/artist/3902",
    "official homepage": "http://www.ninjatune.net/coldcut/",
    "purchase for download": "http://www.junodownload.com/artists/Coldcut",
    "social network": "https://twitter.com/Coldcut",
    streaming: "https://tidal.com/artist/6277",
    wikidata: "https://www.wikidata.org/wiki/Q698224",
  },
  type: "Group",
};

const fakeArtistTags = [
  {
    artist_mbid: "cedd2cc6-c77f-4104-b333-0547b29e0b71",
    count: 1,
    genre_mbid: "89255676-1f14-4dd8-bbad-fca839d6aff4",
    tag: "electronic",
  },
  {
    artist_mbid: "4f6dd51e-bfd7-4153-ace7-9316d1757a57",
    count: 1,
    tag: "uk hip hop",
  },
  {
    artist_mbid: "4f6dd51e-bfd7-4153-ace7-9316d1757a57",
    count: 1,
    genre_mbid: "6c3503e3-bae3-42de-9e4c-7861f2053fbe",
    tag: "dancehall",
  },
  {
    artist_mbid: "4f6dd51e-bfd7-4153-ace7-9316d1757a57",
    count: 1,
    genre_mbid: "c72a5d45-75a8-4b35-9f48-67e49eb4b5e5",
    tag: "dub",
  },
  {
    artist_mbid: "4f6dd51e-bfd7-4153-ace7-9316d1757a57",
    count: 1,
    tag: "uk",
  },
  {
    artist_mbid: "4f6dd51e-bfd7-4153-ace7-9316d1757a57",
    count: 2,
    genre_mbid: "52faa157-6bad-4d86-a0ab-d4dec7d2513c",
    tag: "hip hop",
  },
];

export default function ArtistPage(props: ArtistPageProps): JSX.Element {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { artist: initialArtist, popular_tracks } = props;

  const [artist, setArtist] = React.useState(initialArtist);
  const [popularTracks, setPopularTracks] = React.useState(popular_tracks);
  const [loading, setLoading] = React.useState(false);

  //   const onClickSimilarArtist: React.MouseEventHandler<HTMLElement> = (
  //     event
  //   ) => {
  //     setLoading(true);
  //   	try{
  //     // Hit the API to get all the required info for the artist we clicked on
  //    const response = await fetch(…)
  //   if(!response.ok){
  // 	throw new Error(response.status);
  //   }
  //	setArtist(response.artist)
  // }
  // catch(err){
  // toast.error(<ToastMsg title={"Could no load similar artist"} message={err.toString()})
  // }
  //     setLoading(false);
  //   };

  const listensFromJSPFTracks = popular_tracks ?? [];
  return (
    <div id="artist-page">
      <Loader isLoading={loading} />
      <div
        className="artist-page-header"
        style={{ maxHeight: "500px", display: "flex", padding: "2em" }}
      >
        <div className="cover-art" style={{ aspectRatio: 1, height: "100%" }}>
          Cover Art here
        </div>
        <div className="artist-info">
          <h3>{artist.name}</h3>
          <div>date</div>
          <div>country</div>
        </div>
        <div className="artist-listening-stats">
          Listening stats
          <div>
            123 <FontAwesomeIcon icon={faUserAstronaut} />
          </div>
          <div>
            123 <FontAwesomeIcon icon={faHeadphones} />
          </div>
        </div>
        <TagsComponent
          key={artist.name}
          tags={sortBy(artist_tags, "count")}
          entityType="artist"
          entityMBID={artist.name}
        />
      </div>
      <div className="artist-page-content">
        <div className="">
          <h3>Popular tracks</h3>
          {Array.from(Array(5).keys()).map(() => {
            return (
              <ListenCard
                listen={{
                  listened_at: 0,
                  track_metadata: {
                    artist_name: artist.name,
                    track_name: "Track name",
                  },
                }}
                showTimestamp={false}
                showUsername={false}
              />
            );
          })}
        </div>
        <div className="scroll-start">
          <div className="dragscroll">
            {Array.from(Array(10).keys()).map(() => {
              return (
                <ReleaseCard
                  releaseDate=""
                  releaseMBID=""
                  releaseName=""
                  caaID={null}
                  caaReleaseMBID={null}
                  artistMBIDs={[artist.name]}
                  artistCreditName={artist.name}
                />
              );
            })}
          </div>
        </div>
      </div>
      <BrainzPlayer
        listens={listensFromJSPFTracks}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
        refreshSoundcloudToken={APIService.refreshSoundcloudToken}
      />
    </div>
  );
}

document.addEventListener("DOMContentLoaded", () => {
  const {
    domContainer,
    reactProps,
    globalAppContext,
    sentryProps,
  } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const { artist } = reactProps;

  const ArtistPageWithAlertNotifications = withAlertNotifications(ArtistPage);

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <ToastContainer
        position="bottom-right"
        autoClose={8000}
        hideProgressBar
      />
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <ArtistPageWithAlertNotifications
            artist={fakeArtist}
            artist_tags={fakeArtistTags}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
