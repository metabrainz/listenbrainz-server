import * as React from "react";

export default function ListensOffline() {
  return (
    <>
      <h2 className="page-title">Listens currently unavailable</h2>

      <p>
        The database that contains listens for our users is currently offline
        for maintenance. Please try again in a few minutes.
      </p>

      <p>
        Please note: You may continue to submit listens during this time.
        We&apos;ll save them once our database is available again.
      </p>

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
