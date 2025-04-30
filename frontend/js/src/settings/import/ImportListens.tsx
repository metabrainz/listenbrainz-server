import * as React from "react";

import { Link, useLoaderData } from "react-router-dom";
import { Helmet } from "react-helmet";
import ReactTooltip from "react-tooltip";
import LibreFmImporter from "../../lastfm/LibreFMImporter";
import GlobalAppContext from "../../utils/GlobalAppContext";

type ImportLoaderData = {
  user_has_email: boolean;
  profile_url?: string;
  librefm_api_url: string;
  librefm_api_key: string;
};

export default function Import() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const { name } = currentUser;
  const data = useLoaderData() as ImportLoaderData;
  const {
    user_has_email: userHasEmail,
    profile_url: profileUrl,
    librefm_api_url: librefmApiUrl,
    librefm_api_key: librefmApiKey,
  } = data;
  const apiUrl = APIService.APIBaseURI;

  return (
    <>
      <Helmet>
        <title>Import for {name}</title>
      </Helmet>
      <h2 className="page-title">Import to user {name}</h2>
      {!userHasEmail && (
        <div className="alert alert-danger">
          You have not provided an email address. Please provide an{" "}
          <a href="https://musicbrainz.org/account/edit">email address</a> and{" "}
          <em>verify it</em> to submit listens. Read this{" "}
          <a href="https://blog.metabrainz.org/?p=8915">blog post</a> to
          understand why we need your email. You can provide us with an email on
          your{" "}
          <a href="https://musicbrainz.org/account/edit">MusicBrainz account</a>{" "}
          page.
        </div>
      )}
      <p>
        Import your existing{" "}
        <span className="strong" data-tip data-for="info-tooltip">
          listen
        </span>{" "}
        history from other databases.{" "}
        <ReactTooltip id="info-tooltip" place="top">
          Fun Fact: The term <strong>scrobble</strong> is a trademarked term by
          Last.fm, and we cannot use it.
          <br />
          Instead, we use the term <strong>listen</strong> for our data.
        </ReactTooltip>
        <br />
        To submit <em>new</em> listens, please visit the{" "}
        <a href="https://listenbrainz.org/settings/music-services/details/">
          Connect services
        </a>{" "}
        and <a href="https://listenbrainz.org/add-data/">Submitting data</a>{" "}
        pages.
      </p>

      <h3>Import from Libre.fm</h3>
      <div className="alert alert-warning">
        Looking to import from Last.FM instead? Connect to your LFM account on
        the{" "}
        <Link to="/settings/music-services/details/">
          connect services page
        </Link>
        .
      </div>
      <p>
        The importer manually steps through your listen history and imports the
        listens one page at a time.
      </p>

      <ul>
        <li>
          Should it fail for whatever reason, it is safe to restart the import
          process.
        </li>
        <li>
          Running the import process multiple times <strong>does not</strong>{" "}
          create duplicates in your ListenBrainz listen history.
        </li>
        <li>
          Clicking the &quot;Import listens&quot; button will import your
          profile without the need to open Libre.fm.
        </li>
        <li>
          Your listen counts may not be accurate for up to 24 hours after you
          import your data.{" "}
          <a
            href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html"
            target="_blank"
            rel="noopener noreferrer"
          >
            See more details here.
          </a>
        </li>
      </ul>

      <p>
        You need to keep this page open while it is importing, which may take a
        while.
      </p>

      {userHasEmail && (
        <LibreFmImporter
          user={{
            id: currentUser.id?.toString(),
            name: currentUser.name,
            auth_token: currentUser.auth_token!,
          }}
          profileUrl={profileUrl}
          apiUrl={apiUrl}
          librefmApiUrl={librefmApiUrl}
          librefmApiKey={librefmApiKey}
        />
      )}
    </>
  );
}
