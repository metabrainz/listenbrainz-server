import * as React from "react";
import { Link } from "react-router-dom";

export default function TermsOfService() {
  return (
    <>
      <h2 className="page-title">Terms of Service</h2>

      <p>
        As one of the projects of the{" "}
        <a href="https://metabrainz.org/projects">MetaBrainz Foundation</a>,
        ListenBrainz&apos; terms of service are defined by the social contract
        and privacy policies of the Foundation. You will find these detailed on
        the MetaBrainz website:
      </p>
      <ul>
        <li>
          <a href="https://metabrainz.org/social-contract">Social Contract</a>
        </li>
        <li>
          <a href="https://metabrainz.org/privacy">Privacy Policy</a>
        </li>
        <li>
          <a href="https://metabrainz.org/gdpr">GDPR Compliance</a>
        </li>
        <li>
          <a href="https://metabrainz.org/code-of-conduct">Code of Conduct</a>
        </li>
        <li>
          <a href="https://metabrainz.org/conflict-policy">
            Conflict Resolution Policy
          </a>
        </li>
      </ul>

      <h3>Third party resources</h3>
      <p>
        Additionally, we use the following third party resources to enable you
        to play music on ListenBrainz:
      </p>
      <ul>
        <li>
          <b>
            <a href="https://developer.spotify.com/documentation/web-playback-sdk/">
              Spotify web player SDK
            </a>
          </b>
          : Only loaded if you{" "}
          <Link to="/settings/music-services/details/">
            linked you Spotify pro account
          </Link>
        </li>
        <li>
          <b>
            <a href="https://developers.google.com/youtube/iframe_api_reference">
              Youtube embedded player
            </a>
          </b>
          : This is always loaded and serves as our backup player. The search is
          not as precise as other music services but it enables playback for
          everyone by default
        </li>
        <li>
          <b>
            <a href="https://developers.soundcloud.com/docs/api/html5-widget">
              Soundcloud player widget
            </a>
          </b>
          : Always loaded, only used to play Soundcloud URLs
        </li>
      </ul>
      <p>
        We use the YouTube API Services to search for and play music directly on
        ListenBrainz. By using ListenBrainz to play music, you agree to be bound
        by the YouTube Terms of Service. See their ToS and privacy policy below:
      </p>
      <ul>
        <li>
          <a href="https://www.youtube.com/t/terms">Youtube Terms of Service</a>
        </li>
        <li>
          <a href="https://policies.google.com/privacy">
            Google Privacy Policy
          </a>
        </li>
      </ul>
    </>
  );
}
