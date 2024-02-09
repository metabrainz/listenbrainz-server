import * as React from "react";

import { Link, useLoaderData } from "react-router-dom";
import { Helmet } from "react-helmet";
import LastFmImporter from "../../lastfm/LastFMImporter";
import GlobalAppContext from "../../utils/GlobalAppContext";

type ImportLoaderData = {
  user_has_email: boolean;
  profile_url?: string;
  lastfm_api_url: string;
  lastfm_api_key: string;
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
    lastfm_api_url: lastfmApiUrl,
    lastfm_api_key: lastfmApiKey,
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
          <em>verify it</em> to submit listens. Read this
          <a href="https://blog.metabrainz.org/?p=8915">blog post</a>
          to understand why we need your email. You can provide us with an email
          on your
          <a href="https://musicbrainz.org/account/edit">
            MusicBrainz account
          </a>{" "}
          page.
        </div>
      )}
      <p>
        Most users will want to import from Last.fm directly.
        <br />
        Fun Fact: The term <strong>scrobble</strong> is a trademarked term by
        Last.fm, and we cannot use it. Instead, we use the term{" "}
        <strong>listen</strong> for our data.
      </p>

      <h3>Direct import from Last.fm and Libre.fm</h3>
      <p>
        The importer manually steps through your listen history and imports the
        listens one page at a time. Should it fail for whatever reason, it is
        safe to restart the import process. Running the import process multiple
        times <strong>does not</strong> create duplicates in your ListenBrainz
        listen history.
      </p>
      <p>
        In order for this to work, you must disable the &#34;Hide recent
        listening information&#34; setting in your Last.fm{" "}
        <a href="https://www.last.fm/settings/privacy">Privacy Settings</a>.
      </p>
      <p>
        Clicking the &quot;Import listens&quot; button will import your profile
        now without the need to open LastFM.
        <br />
        You need to keep this page open for the tool to work, it might take a
        while to complete. Though, you can continue doing your work. :)
      </p>
      <p>
        <em>NOTE</em>: Please note that your listen counts may not be accurate
        for up to 24 hours after you import your data!
        <a
          href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html"
          target="_blank"
          rel="noopener noreferrer"
        >
          See more details here.
        </a>
        <br />
        Also, running the Last.fm importer twice will not cause duplicates in
        your listen history.
      </p>
      {userHasEmail && (
        <LastFmImporter
          user={{
            id: currentUser.id?.toString(),
            name: currentUser.name,
            auth_token: currentUser.auth_token!,
          }}
          profileUrl={profileUrl}
          apiUrl={apiUrl}
          lastfmApiUrl={lastfmApiUrl}
          lastfmApiKey={lastfmApiKey}
          librefmApiUrl={librefmApiUrl}
          librefmApiKey={librefmApiKey}
        />
      )}
      <h4> Reset Last.FM Import timestamp </h4>
      <p>
        If you think that a partial import has somehow missed some listens, you
        may reset your previous import timestamp. This will cause your next
        import to be a complete import which should add any missing listens
        while still avoiding adding duplicates to your history.
      </p>

      <p>If you want to reset your previous import timestamp, click below</p>
      <p>
        <span className="btn btn-info btn-lg" style={{ width: "300px" }}>
          <Link to="/settings/resetlatestimportts/" style={{ color: "white" }}>
            Reset Import Timestamp
          </Link>
        </span>
      </p>
    </>
  );
}
