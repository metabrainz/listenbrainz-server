/* eslint-disable import/no-unresolved */
import { Navigation, Keyboard, EffectCoverflow } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/react";
import "swiper/css/bundle";
import React from "react";
import {
  generateAlbumArtThumbnailLink,
  getStatsArtistLink,
} from "../../../utils/utils";
import { getEntityLink } from "../../stats/utils";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import ImageShareButtons from "./ImageShareButtons";
/* eslint-enable import/no-unresolved */

function AlbumsCoverflow(props: {
  topReleaseGroups: UserReleaseGroupsResponse["payload"]["release_groups"];
}) {
  const { topReleaseGroups } = props;
  return (
    <div id="top-albums">
      <Swiper
        modules={[Navigation, Keyboard, EffectCoverflow]}
        spaceBetween={15}
        slidesPerView={2}
        initialSlide={0}
        centeredSlides
        navigation
        effect="coverflow"
        coverflowEffect={{
          rotate: 40,
          depth: 100,
          slideShadows: false,
        }}
        breakpoints={{
          700: {
            initialSlide: 2,
            spaceBetween: 100,
            slidesPerView: 3,
            coverflowEffect: {
              rotate: 20,
              depth: 300,
              slideShadows: false,
            },
          },
        }}
      >
        {topReleaseGroups.slice(0, 50).map((release_group) => {
          if (!release_group.caa_id || !release_group.caa_release_mbid) {
            return null;
          }
          const coverArt = generateAlbumArtThumbnailLink(
            release_group.caa_id,
            release_group.caa_release_mbid,
            500
          );
          return (
            <SwiperSlide
              lazy
              key={`coverflow-${release_group.release_group_name}`}
            >
              <img
                data-src={coverArt ?? "/static/img/cover-art-placeholder.jpg"}
                alt={release_group.release_group_name}
                className="swiper-lazy"
                loading="lazy"
              />
              <div className="swiper-lazy-preloader swiper-lazy-preloader-white" />
              <div title={release_group.release_group_name}>
                {getEntityLink(
                  "release-group",
                  release_group.release_group_name,
                  release_group.release_group_mbid
                )}
                <div className="small text-muted">
                  {getStatsArtistLink(
                    release_group.artists,
                    release_group.artist_name,
                    release_group.artist_mbids
                  )}
                </div>
              </div>
            </SwiperSlide>
          );
        })}
      </Swiper>
    </div>
  );
}

type YIMTopAlbumsProps = {
  topReleaseGroups: UserReleaseGroupsResponse["payload"]["release_groups"];
  userName: string;
  year: number;
};
export default function YIMTopAlbums({
  topReleaseGroups,
  userName,
  year,
}: YIMTopAlbumsProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const encodedUsername = encodeURIComponent(userName);
  const linkToUserProfile = `https://listenbrainz.org/user/${encodedUsername}`;
  const linkToThisPage = `${linkToUserProfile}/year-in-music/${year}`;
  if (!topReleaseGroups || topReleaseGroups.length === 0) {
    return null;
  }
  return (
    <div className="section">
      <div className="card content-card" id="top-releases">
        <h3 className="flex-center">Top albums of {year}</h3>
        <AlbumsCoverflow topReleaseGroups={topReleaseGroups} />
        <div className="yim-share-button-container">
          <ImageShareButtons
            svgURL={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=albums`}
            shareUrl={`${linkToThisPage}#top-albums`}
            // shareText="Check out my"
            shareTitle={`My top albums of ${year}`}
            fileName={`${userName}-top-albums-${year}`}
            // customStyles={imageShareCustomStyles}
          />
        </div>
      </div>
    </div>
  );
}
