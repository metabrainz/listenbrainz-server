import * as React from "react";

export default function MusicBrainzOffline() {
  return (
    <>
      <h2 className="page-title">Login currently unavailable</h2>

      <p>
        ListenBrainz login and sign up is currently unavailable due to database
        maintenance. Please try again in a few minutes.
      </p>

      <p>Please note: You may continue to submit listens during this time.</p>

      <p>
        You may find out more about the current status of our services by
        checking our{" "}
        <a href="https://mastodon.social/@ListenBrainz">Mastodon</a>
        or <a href="https://bsky.app/profile/listenbrainz.org">Bluesky</a>{" "}
        feeds.
      </p>
    </>
  );
}
