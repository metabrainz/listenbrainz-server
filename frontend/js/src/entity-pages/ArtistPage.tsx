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
import { pick, sortBy } from "lodash";
import tinycolor from "tinycolor2";
import withAlertNotifications from "../notifications/AlertNotificationsHOC";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ErrorBoundary from "../utils/ErrorBoundary";
import { getAverageRGBOfImage, getPageProps } from "../utils/utils";
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

const fakeData = {
  area: "United Kingdom",
  artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
  begin_year: 1991,
  name: "Portishead",
  rels: {
    "free streaming": "https://www.deezer.com/artist/1069",
    lyrics: "https://muzikum.eu/en/122-6105/portishead/lyrics.html",
    "official homepage": "http://www.portishead.co.uk/",
    "purchase for download":
      "https://www.junodownload.com/artists/Portishead/releases/",
    "social network": "https://www.facebook.com/portishead",
    streaming: "https://tidal.com/artist/27441",
    wikidata: "https://www.wikidata.org/wiki/Q191352",
    youtube: "https://www.youtube.com/user/portishead1002",
  },
  type: "Group",
  tag: {
    artist: [
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 1,
        tag: "the lost generation",
      },
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 6,
        genre_mbid: "89255676-1f14-4dd8-bbad-fca839d6aff4",
        tag: "electronic",
      },
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 4,
        genre_mbid: "65c97e89-b42b-45c2-a70e-0eca1b8f0ff7",
        tag: "experimental rock",
      },
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 1,
        genre_mbid: "6e2e809f-8c54-4e0f-aca0-0642771ab3cf",
        tag: "electro-industrial",
      },
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 7,
        tag: "trip-hop",
      },
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 3,
        tag: "british",
      },
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 1,
        genre_mbid: "ec5a14c7-7793-46dc-b858-470183eb63f7",
        tag: "folktronica",
      },
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 11,
        genre_mbid: "45eb1d9c-588c-4dc8-9394-a14b7c8f02bc",
        tag: "trip hop",
      },
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 2,
        genre_mbid: "ba318056-9ddf-46cd-8b95-61fc993b962d",
        tag: "krautrock",
      },
      {
        artist_mbid: "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        count: 9,
        genre_mbid: "cc38aba3-48ed-439a-83b9-f81a34a66598",
        tag: "downtempo",
      },
    ],
  },
};

export default function ArtistPage(props: ArtistPageProps): JSX.Element {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { artist: initialArtist, popular_tracks, artist_tags } = props;

  const [artist, setArtist] = React.useState(initialArtist);
  const [popularTracks, setPopularTracks] = React.useState(popular_tracks);
  const [artistTags, setArtistTags] = React.useState(artist_tags);
  const [loading, setLoading] = React.useState(false);

  /** Album art and album color related */
  const coverArtSrc = "/static/img/cover-art-placeholder.jpg";
  const albumArtRef = React.useRef<HTMLImageElement>(null);
  const [albumArtColor, setAlbumArtColor] = React.useState({
    r: 0,
    g: 0,
    b: 0,
  });
  React.useEffect(() => {
    const setAverageColor = () => {
      const averageColor = getAverageRGBOfImage(albumArtRef?.current);
      setAlbumArtColor(averageColor);
    };
    const currentAlbumArtRef = albumArtRef.current;
    if (currentAlbumArtRef) {
      currentAlbumArtRef.addEventListener("load", setAverageColor);
    }
    return () => {
      if (currentAlbumArtRef) {
        currentAlbumArtRef.removeEventListener("load", setAverageColor);
      }
    };
  }, [setAlbumArtColor]);

  const adjustedAlbumColor = tinycolor.fromRatio(albumArtColor);
  adjustedAlbumColor.saturate(20);
  adjustedAlbumColor.setAlpha(0.6);

  /** Navigation from one artist to a similar artist */
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
  //  setArtistTags(…)
  //  setPopularTracks(…)
  // }
  // catch(err){
  // toast.error(<ToastMsg title={"Could no load similar artist"} message={err.toString()})
  // }
  //     setLoading(false);
  //   };

  const listensFromJSPFTracks = popular_tracks ?? [];
  return (
    <div
      id="artist-page"
      style={{ ["--bg-color" as string]: adjustedAlbumColor }}
    >
      <Loader isLoading={loading} />
      <div className="artist-page-header flex">
        <div className="cover-art">
          <img
            src={coverArtSrc}
            ref={albumArtRef}
            crossOrigin="anonymous"
            alt="Album art"
          />
        </div>
        <div className="artist-info">
          <h3>{artist.name}</h3>
          <div>
            <small>{artist.begin_year}</small>
          </div>
          <div>{artist.area}</div>
        </div>
        <div className="listening-stats">
          Listening stats
          <div>
            123 <FontAwesomeIcon icon={faUserAstronaut} />
          </div>
          <div>
            123 <FontAwesomeIcon icon={faHeadphones} />
          </div>
        </div>
      </div>
      <div className="tags">
        <TagsComponent
          key={artist.name}
          tags={sortBy(artistTags, "count")}
          entityType="artist"
          entityMBID={artist.name}
        />
      </div>
      <div className="artist-page-content">
        <div className="tracks">
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
          <button className="btn btn-info btn-block">See more…</button>
        </div>
        <div className="reviews">
          <h3>Reviews</h3>
          <button className="btn btn-info btn-block">See more…</button>
        </div>
        <div className="full-width scroll-start">
          <h3>Albums</h3>
          <div className="dragscroll flex">
            {Array.from(Array(10).keys()).map(() => {
              return (
                // <ReleaseCard
                //   releaseDate=""
                //   releaseMBID=""
                //   releaseName=""
                //   caaID={null}
                //   caaReleaseMBID={null}
                //   artistMBIDs={[artist.name]}
                //   artistCreditName={artist.name}
                // />
                <div className="cover-art">Album cover here</div>
              );
            })}
          </div>
        </div>
        <div className="similarity">
          <h3>Similar artists</h3>
          Artist similarity here
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
  const { artist_data } = reactProps;
  const { tag, ...artist_metadata } = fakeData;

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
            artist={artist_metadata}
            artist_tags={tag?.artist}
          />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
