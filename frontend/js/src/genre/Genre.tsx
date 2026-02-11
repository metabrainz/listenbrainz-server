import * as React from "react";
import { Link, useLocation, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlayCircle } from "@fortawesome/free-solid-svg-icons";
import DOMPurify from "dompurify";
import { groupBy, orderBy, sortBy } from "lodash";
import { RouteQuery } from "../utils/Loader";
import OpenInMusicBrainzButton from "../components/OpenInMusicBrainz";
import ReleaseCard from "../explore/fresh-releases/components/ReleaseCard";
import HorizontalScrollContainer from "../components/HorizontalScrollContainer";
import ListenCard from "../common/listens/ListenCard";
import { recordingToListen } from "../track/Track";
import { formatListenCount } from "../explore/fresh-releases/utils";
import { getEntityLink } from "../user/stats/utils";
import type {
  GenrePageProps,
  TaggedArtistEntity,
  TaggedReleaseGroupEntity,
  TaggedRecordingEntity,
} from "./types";
import {
  COVER_ART_SINGLE_ROW_COUNT,
  SortingButtons,
  typeOrder,
} from "../artist/ArtistPage";

function sortReleaseGroupsForGenre(
  sort: "release_date" | "total_listen_count",
  releaseGroups: TaggedReleaseGroupEntity[]
) {
  return orderBy(
    releaseGroups,
    [
      sort === "release_date"
        ? (rg) => rg.date || ""
        : (rg) => rg.total_listen_count ?? 0,
      sort === "release_date"
        ? (rg) => rg.total_listen_count ?? 0
        : (rg) => rg.date || "",
      "name",
    ],
    ["desc", "desc", "asc"]
  );
}

function getReleaseCard(rg: TaggedReleaseGroupEntity) {
  const artistCreditName =
    rg.artist_credit_name ??
    rg.artists?.map((ar) => ar.artist_credit_name + ar.join_phrase).join("") ??
    "";
  const artistMBIDs = rg.artists?.map((ar) => ar.artist_mbid) ?? [];
  return (
    <ReleaseCard
      key={rg.mbid}
      releaseDate={rg.date ?? undefined}
      dateFormatOptions={{ year: "numeric", month: "short" }}
      releaseGroupMBID={rg.mbid}
      releaseName={rg.name}
      releaseTypePrimary={rg.type ?? undefined}
      artistCredits={rg.artists}
      artistCreditName={artistCreditName}
      artistMBIDs={artistMBIDs}
      caaID={rg.caa_id ?? null}
      caaReleaseMBID={rg.caa_release_mbid ?? null}
      showInformation
      showArtist
      showReleaseTitle
      showListens
      listenCount={rg.total_listen_count ?? undefined}
    />
  );
}

export default function GenrePage(): JSX.Element {
  const location = useLocation();
  const params = useParams() as { genreMBID: string };
  const { data } = useQuery<GenrePageProps>(
    RouteQuery(["genre", params], location.pathname)
  );

  const { genre, genre_mbid, entities, coverArt: coverArtSVG } =
    data || ({} as GenrePageProps);
  const { name } = genre || {};

  const [sort, setSort] = React.useState<"release_date" | "total_listen_count">(
    "release_date"
  );
  const [expandDiscography, setExpandDiscography] = React.useState(false);

  const { data: wikipediaExtractData } = useQuery<{
    wikipediaExtract?: WikipediaExtract;
  }>({
    queryKey: ["wikipedia-extract", genre_mbid],
    queryFn: async () => {
      const response = await fetch(
        `https://musicbrainz.org/genre/${genre_mbid}/wikipedia-extract`
      );
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body?.message ?? response.statusText);
      }
      return body;
    },
    enabled: Boolean(genre_mbid),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const wikipediaExtract = wikipediaExtractData?.wikipediaExtract;

  const artists: TaggedArtistEntity[] = entities?.artist?.entities ?? [];
  const recordings: TaggedRecordingEntity[] =
    entities?.recording?.entities ?? [];
  const releaseGroups: TaggedReleaseGroupEntity[] =
    entities?.release_group?.entities ?? [];
  const rgGroups = groupBy(releaseGroups, (rg) => rg.type ?? "Other");
  const last = Object.keys(rgGroups).length;
  const sortedRgGroupsKeys = sortBy(Object.keys(rgGroups), (type) =>
    typeOrder.indexOf(type) !== -1 ? typeOrder.indexOf(type) : last
  );
  const groupedReleaseGroups: Record<string, TaggedReleaseGroupEntity[]> = {};
  sortedRgGroupsKeys.forEach((type) => {
    groupedReleaseGroups[type] = sortReleaseGroupsForGenre(
      sort,
      rgGroups[type]
    );
  });
  const releaseGroupTypesNames = Object.entries(groupedReleaseGroups);
  const showFullDiscographyButton =
    releaseGroupTypesNames.reduce(
      (rows, curr) =>
        rows + (curr[1].length > COVER_ART_SINGLE_ROW_COUNT ? 2 : 1),
      0
    ) > 4;

  if (!genre) {
    return <div>Loading...</div>;
  }

  return (
    <div id="entity-page" role="main" className="genre-page">
      <Helmet>
        <title>{name}</title>
      </Helmet>
      <div className="entity-page-header flex">
        <div
          className="cover-art"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(
              coverArtSVG ??
                "<img src='/static/img/cover-art-placeholder.jpg' alt=''></img>"
            ),
          }}
          title={name ? `Cover art for ${name}` : undefined}
        />
        <div className="genre-info">
          <h1>{name}</h1>
          <div className="details" />
          {wikipediaExtract && (
            <div className="wikipedia-extract">
              <div
                className="content"
                // eslint-disable-next-line react/no-danger
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(wikipediaExtract.content),
                }}
              />
              <a
                className="btn btn-link pull-right"
                href={wikipediaExtract.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Read on Wikipedia…
              </a>
            </div>
          )}
        </div>
        <div className="right-side gap-1">
          <div className="entity-rels">
            <OpenInMusicBrainzButton
              entityType="genre"
              entityMBID={genre_mbid}
            />
          </div>
          <div className="btn-group lb-radio-button">
            <Link
              type="button"
              className="btn btn-info"
              to={`/explore/lb-radio/?prompt=tag:(${encodeURIComponent(
                name
              )})&mode=easy`}
            >
              <FontAwesomeIcon icon={faPlayCircle} /> Radio
            </Link>
            <button
              type="button"
              className="btn btn-info dropdown-toggle px-3"
              data-bs-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="false"
              aria-label="Toggle dropdown"
            />
            <div className="dropdown-menu">
              <Link
                to={`/explore/lb-radio/?prompt=tag:(${encodeURIComponent(
                  name
                )})&mode=easy`}
                className="dropdown-item"
              >
                Genre radio
              </Link>
              <Link
                to={`/explore/lb-radio/?prompt=tag:(${encodeURIComponent(
                  name
                )})::nosim&mode=easy`}
                className="dropdown-item"
              >
                This genre only
              </Link>
            </div>
          </div>
        </div>
      </div>
      <div className="entity-page-content">
        {artists.length > 0 && (
          <div>
            <h3 className="header-with-line">Top artists</h3>
            <div className="top-entity-listencards">
              {artists.map((artist) => (
                <ListenCard
                  key={artist.mbid}
                  listen={{
                    listened_at: 0,
                    track_metadata: {
                      track_name: "",
                      artist_name: artist.name,
                      additional_info: {
                        artist_mbids: [artist.mbid],
                      },
                    },
                  }}
                  listenDetails={getEntityLink(
                    "artist",
                    artist.name,
                    artist.mbid
                  )}
                  showTimestamp={false}
                  showUsername={false}
                  additionalActions={
                    artist.total_listen_count != null ? (
                      <span className="badge bg-info">
                        {formatListenCount(artist.total_listen_count)}
                      </span>
                    ) : undefined
                  }
                  customThumbnail={
                    <div
                      className="listen-thumbnail"
                      style={{ minWidth: "0" }}
                    />
                  }
                  compact
                />
              ))}
            </div>
          </div>
        )}
        {recordings.filter((r) => r.recording_name).length > 0 && (
          <div>
            <h3 className="header-with-line">Top recordings</h3>
            <div className="top-entity-listencards">
              {recordings
                .filter((r) => r.recording_name)
                .map((rec) => (
                  <ListenCard
                    key={rec.recording_mbid}
                    listen={recordingToListen(rec)}
                    showTimestamp={false}
                    showUsername={false}
                  />
                ))}
            </div>
          </div>
        )}
        <div
          className={`discography ${
            expandDiscography || !showFullDiscographyButton ? "expanded" : ""
          }`}
        >
          {releaseGroupTypesNames.map(([type, rgGroup]) => (
            <div className="albums" key={type}>
              <div className="listen-header">
                <h3 className="header-with-line">{type}</h3>
                <SortingButtons sort={sort} setSort={setSort} />
              </div>
              <HorizontalScrollContainer
                className={`cover-art-container ${
                  rgGroup.length <= COVER_ART_SINGLE_ROW_COUNT
                    ? "single-row"
                    : ""
                }`}
              >
                {rgGroup.map(getReleaseCard)}
              </HorizontalScrollContainer>
            </div>
          ))}
          {showFullDiscographyButton && (
            <div className="read-more mb-3">
              <button
                type="button"
                className="btn btn-outline-info"
                onClick={() => setExpandDiscography((prevValue) => !prevValue)}
              >
                See {expandDiscography ? "less" : "full discography"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
