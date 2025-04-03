import * as React from "react";
import { Helmet } from "react-helmet";
import { useLocation } from "react-router-dom";

type SEOProps = {
  year: number;
  userName: string;
};

export function YIMYearMetaTags({
  year,
  backgroundColor,
}: {
  year: number;
  backgroundColor?: string;
}) {
  if (year === 2021) {
    return (
      <Helmet>
        <meta
          property="og:image"
          content="https://listenbrainz.org/static/img/year-in-music-2021.png"
        />
        <meta
          property="twitter:image"
          content="https://listenbrainz.org/static/img/year-in-music-2021.png"
        />
      </Helmet>
    );
  }
  if (year === 2022) {
    return (
      <Helmet>
        <meta
          property="og:image"
          content="https://listenbrainz.org/static/img/year-in-music-22/yim22-logo.png"
        />
        <meta
          property="twitter:image"
          content="https://listenbrainz.org/static/img/year-in-music-22/yim22-logo.png"
        />
        <style type="text/css">
          {`body>.container, body>.container-fluid {
            margin:0;
            padding:0;
            width: 100%;
          }
          section.footer{
              display: none;
          }`}
        </style>
      </Helmet>
    );
  }
  if (year === 2023) {
    return (
      <Helmet>
        <meta
          property="og:image"
          content="https://listenbrainz.org/static/img/year-in-music-23/yim-23-header.png"
        />
        <meta
          property="twitter:image"
          content="https://listenbrainz.org/static/img/year-in-music-23/yim-23-header.png"
        />
        <meta property="og:image:type" content="image/png" />
        <style type="text/css">
          {`body>*:not(nav) {
              margin:0;
              padding:0;
              background-color: #F0EEE2
            }
            section.footer{
              display: none;
            }`}
        </style>
      </Helmet>
    );
  }
  return (
    <Helmet>
      <meta
        property="og:image"
        content="https://listenbrainz.org/static/img/year-in-music-24/yim-24-header.png"
      />
      <meta
        property="twitter:image"
        content="https://listenbrainz.org/static/img/year-in-music-24/yim-24-header.png"
      />
      <meta property="og:image:type" content="image/png" />
      <style type="text/css">
        {`body>*:not(nav) {
            margin:0;
            padding:0;
            background-color: ${backgroundColor};
          }
          section.footer{
            display: none;
          }`}
      </style>
      <style type="text/css">
        {`
        @import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;900");
      `}
      </style>
    </Helmet>
  );
}

export default function SEO(props: SEOProps) {
  const { year, userName } = props;
  const location = useLocation();

  const urlString = new URL(
    location.pathname,
    "https://listenbrainz.org"
  ).toString();

  return (
    <Helmet>
      <title>{`Year in Music ${year} for ${userName}`}</title>
      <meta
        name="description"
        content={`Check out the music review for ${year} that @ListenBrainz created from my listening history!`}
      />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content="@listenbrainz" />
      <meta property="og:url" content={urlString} />
      <meta property="og:type" content="website" />
      <meta
        property="og:title"
        content={`ListenBrainz Year in Music for ${userName}`}
      />
      <meta
        property="og:description"
        content={`Check out the music review for ${year} that @ListenBrainz created from my listening history!`}
      />
      <meta property="twitter:url" content={urlString} />
      <meta
        property="twitter:title"
        content={`ListenBrainz Year in Music for ${userName}`}
      />
      <meta property="twitter:domain" content="listenbrainz.org" />
      <meta
        property="twitter:description"
        content={`Check out the music review for ${year} that @ListenBrainz created from my listening history!`}
      />
      <meta
        property="og:image"
        content="https://listenbrainz.org/static/img/year-in-music-23/yim-23-header.png"
      />
      <meta
        property="twitter:image"
        content="https://listenbrainz.org/static/img/year-in-music-23/yim-23-header.png"
      />
      <meta property="og:image:type" content="image/png" />
    </Helmet>
  );
}
