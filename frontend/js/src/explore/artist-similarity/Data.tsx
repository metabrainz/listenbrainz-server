import React, { useCallback, useContext, useEffect, useState } from "react";
import tinycolor from "tinycolor2";
import { toast } from "react-toastify";
import SimilarArtistsGraph from "./SimilarArtistsGraph";
import SearchBox from "./artist-search/SearchBox";
import Panel from "./artist-panel/Panel";
import { ToastMsg } from "../../notifications/Notifications";
import generateTransformedArtists from "./generateTransformedArtists";
import BrainzPlayer from "../../brainzplayer/BrainzPlayer";
import GlobalAppContext from "../../utils/GlobalAppContext";

type ArtistType = {
  artist_mbid: string;
  name: string;
  comment?: string;
  type?: string;
  gender?: string;
  score?: number;
  reference_mbid?: string;
};

type MarkupResponseType = {
  data: string;
  type: "markup";
};

type DatasetResponseType = {
  columns: Array<string>;
  data: Array<ArtistType>;
  type: "dataset";
};

type ApiResponseType = Array<MarkupResponseType | DatasetResponseType>;

type NodeType = {
  id: string;
  artist_mbid: string;
  artist_name: string;
  size: number;
  color: string;
  score: number;
};

type LinkType = {
  source: string;
  target: string;
  distance: number;
};

type GraphDataType = {
  nodes: Array<NodeType>;
  links: Array<LinkType>;
};

const colorGenerator = (): [tinycolor.Instance, tinycolor.Instance] => {
  const initialColor = tinycolor(`hsv(${Math.random() * 360}, 100%, 90%)`);
  return [initialColor, initialColor.clone().tetrad()[1]];
};

const ARTIST_MBID = "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11";
const SIMILAR_ARTISTS_LIMIT_VALUE = 18;
const BASE_URL =
  "https://labs.api.listenbrainz.org/similar-artists/json?algorithm=session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30&artist_mbid=";
// Apha value of the background color of the graph
const BACKGROUND_ALPHA = 0.2;

function Data() {
  const [similarArtistsList, setSimilarArtistsList] = useState<
    Array<ArtistType>
  >([]);
  // State to store the complete list of similar artists to help with when user changes artist limit
  const [completeSimilarArtistsList, setCompleteSimilarArtistsList] = useState<
    Array<ArtistType>
  >([]);
  const [mainArtist, setMainArtist] = useState<ArtistType>();
  const [similarArtistsLimit, setSimilarArtistsLimit] = useState(
    SIMILAR_ARTISTS_LIMIT_VALUE
  );
  const [colors, setColors] = useState(colorGenerator);

  const [artistMBID, setArtistMBID] = useState(ARTIST_MBID);

  const testCurrentTrack: Array<Listen> = [
    {
      listened_at: 0,
      track_metadata: {
        artist_name: "Arjan Dhillon",
        track_name: "Danabaad",
        // release_name: "Awara",
        // recording_mbid: "908a8f0f-1e08-45b4-94cb-0458280d0889",
        // release_mbid: "d8c0026f-e10c-494d-b66c-2085062b8c2e",
      },
    },
  ];

  const [currentTracks, setCurrentTracks] = useState<Array<Listen>>();

  const processData = useCallback((dataResponse: ApiResponseType): void => {
    // Type guard for dataset response
    const isDatasetResponse = (
      response: MarkupResponseType | DatasetResponseType
    ): response is DatasetResponseType => {
      return response.type === "dataset";
    };
    // Get the datasets out of the API response
    const artistsData = dataResponse.filter(isDatasetResponse);
    if (artistsData.length) {
      // Get the main artist from the first dataset
      setMainArtist(artistsData[0].data[0]);
      // Get the similar artists from the second dataset
      const similarArtistsResponse = artistsData[1];
      if (similarArtistsResponse.data.length) {
        setCompleteSimilarArtistsList(similarArtistsResponse.data);
      }
      // In case no similar artists are found
      else {
        setCompleteSimilarArtistsList([]);
      }
    }
    setColors((prevColors) => [prevColors[1], prevColors[1].tetrad()[1]]);
  }, []);

  const transformedArtists: GraphDataType = mainArtist
    ? generateTransformedArtists(
        mainArtist,
        similarArtistsList,
        colors[0],
        colors[1],
        similarArtistsLimit
      )
    : {
        nodes: [],
        links: [],
      };

  const fetchData = useCallback(
    async (artist_mbid: string): Promise<void> => {
      try {
        const response = await fetch(BASE_URL + artist_mbid);
        const data = await response.json();
        processData(data);
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
    [processData]
  );

  // Update the graph when either artistMBID or similarArtistsLimit changes
  useEffect(() => {
    fetchData(artistMBID);
  }, [artistMBID, fetchData]);
  // Update the graph when limit changes by only changing the data and not making a new request to server
  useEffect(() => {
    const newSimilarArtistsList = completeSimilarArtistsList.slice(
      0,
      similarArtistsLimit
    );
    setSimilarArtistsList(newSimilarArtistsList);
  }, [completeSimilarArtistsList, similarArtistsLimit]);

  useEffect(() => {
    window.postMessage(
      { brainzplayer_event: "current-listen-change", payload: currentTracks },
      window.location.origin
    );
    window.postMessage(
      { brainzplayer_event: "play-listen", payload: currentTracks },
      window.location.origin
    );
  }, [currentTracks]);

  const backgroundColor1 = colors[0]
    .clone()
    .setAlpha(BACKGROUND_ALPHA)
    .toRgbString();
  const backgroundColor2 = colors[1]
    .clone()
    .setAlpha(BACKGROUND_ALPHA)
    .toRgbString();
  const backgroundGradient = `linear-gradient(${
    Math.random() * 360
  }deg ,${backgroundColor1},${backgroundColor2})`;
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  return (
    <div className="artist-similarity-main-container">
      <SearchBox
        onArtistChange={setArtistMBID}
        onSimilarArtistsLimitChange={setSimilarArtistsLimit}
        currentsimilarArtistsLimit={similarArtistsLimit}
      />
      <div className="artist-similarity-graph-panel-container">
        <SimilarArtistsGraph
          onArtistChange={setArtistMBID}
          data={transformedArtists}
          background={backgroundGradient}
        />
        {mainArtist && (
          <Panel artist={mainArtist} onTrackChange={setCurrentTracks} />
        )}
      </div>
      {currentTracks && (
        <BrainzPlayer
          listens={currentTracks}
          listenBrainzAPIBaseURI={APIService.APIBaseURI}
          refreshSpotifyToken={APIService.refreshSpotifyToken}
          refreshYoutubeToken={APIService.refreshYoutubeToken}
          refreshSoundcloudToken={APIService.refreshSoundcloudToken}
        />
      )}
    </div>
  );
}

export default Data;
export type { GraphDataType, NodeType, LinkType, ArtistType };
