/* eslint-disable import/no-unresolved */
import { Navigation, Keyboard, EffectCoverflow } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/react";
import "swiper/css/bundle";
/* eslint-enable import/no-unresolved */
import React from "react";
import { isNil } from "lodash";
import {
  generateAlbumArtThumbnailLink,
  getStatsArtistLink,
} from "../../../utils/utils";
import { getEntityLink } from "../../stats/utils";

export default function AlbumsCoverflow(props: {
  topReleaseGroups: UserReleaseGroupsResponse["payload"]["release_groups"];
}) {
  const { topReleaseGroups } = props;
  if (!topReleaseGroups || topReleaseGroups.length === 0) {
    return null;
  }
  return (
    <div id="top-albums" className="card-bg">
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
        onClick={(swiper) => {
          if (!isNil(swiper.clickedIndex)) swiper.slideTo(swiper.clickedIndex);
        }}
        breakpoints={{
          700: {
            initialSlide: 1,
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
              key={`coverflow-${release_group.release_group_name}`}
              // lazy
            >
              {/* <div className="swiper-lazy-preloader" /> */}
              <img
                src={coverArt ?? "/static/img/cover-art-placeholder.jpg"}
                alt={release_group.release_group_name}
                loading="lazy"
              />
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
