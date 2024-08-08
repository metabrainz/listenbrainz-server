import * as React from "react";
import tinycolor from "tinycolor2";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy, faDownload } from "@fortawesome/free-solid-svg-icons";
import { isEmpty, isEqual, kebabCase } from "lodash";
import { useLoaderData, useLocation } from "react-router-dom";
import { Helmet } from "react-helmet";
import { useQuery } from "@tanstack/react-query";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";
import SearchBox from "./components/SearchBox";
import SimilarArtistsGraph from "./components/SimilarArtistsGraph";
import Panel from "./components/Panel";
import generateTransformedArtists from "./utils/generateTransformedArtists";
import { downloadComponentAsImage, copyImageToClipboard } from "./utils/utils";
import { RouteQuery } from "../../utils/Loader";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";

type MusicNeighborhoodLoaderData = {
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

export default function MusicNeighborhood() {
  const location = useLocation();
  const { data } = useQuery<MusicNeighborhoodLoaderData>(
    RouteQuery(["music-neighborhood"], location.pathname)
  );
  const { algorithm: DEFAULT_ALGORITHM, artist_mbid: DEFAULT_ARTIST_MBID } =
    data || {};
  const BASE_URL = `https://labs.api.listenbrainz.org/similar-artists/json?algorithm=${DEFAULT_ALGORITHM}&artist_mbids=`;
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
        link: `/artist/${artistMBID}`,
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
      if (!isEmpty(topAlbumReleaseColor)) {
        const { red, green, blue } = topAlbumReleaseColor;
        firstColor = tinycolor({ r: red, g: green, b: blue });
      } else {
        // Do we want to pick a color from an array of predefined colors instead of random?
        firstColor = tinycolor.random();
      }
      if (
        !isEmpty(topRecordingReleaseColor) &&
        !isEqual(topAlbumReleaseColor, topRecordingReleaseColor)
      ) {
        const { red, green, blue } = topRecordingReleaseColor;
        secondColor = tinycolor({ r: red, g: green, b: blue });
        // We should consider using another color library that allows us to calculate color distance
        // better using deltaE algorithms. Looks into color.js and chroma.js for example.
        const hue1 = firstColor.toHsv().h;
        const hue2 = secondColor.toHsv().h;
        const distanceBetweenColors = Math.min(
          Math.abs(hue2 - hue1),
          360 - Math.abs(hue2 - hue1)
        );
        if (distanceBetweenColors < 25) {
          // Colors are too similar, set up for picking another color below.
          secondColor = undefined;
        }
      }
      if (!secondColor) {
        // If we don't have required release info, base the second color on the first,
        // randomly picking one of the tetrad complementary colors.
        const randomTetradColor = Math.round(Math.random() * (3 - 1) + 1);
        secondColor = tinycolor(firstColor).clone().tetrad()[randomTetradColor];
      }

      // Adjust the colors if they are too light or too dark
      [firstColor, secondColor].forEach((color) => {
        if (isColorTooLight(color)) {
          color.darken(20).saturate(30);
        } else if (isColorTooDark(color)) {
          color.lighten(20).saturate(30);
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
          <SimilarArtistsGraph
            onArtistChange={onArtistChange}
            data={transformedArtists}
            background={backgroundGradient}
            graphParentElementRef={graphParentElementRef}
          />
          {artistInfo && <Panel artistInfo={artistInfo} loading={loading} />}
        </div>
      </div>
    </>
  );
}
