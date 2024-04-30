import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../utils/GlobalAppContext";

export default function Login() {
  const navigate = useNavigate();
  const next = new URLSearchParams(window.location.search).get("next");
  const { currentUser } = React.useContext(GlobalAppContext);

  // If the user is already logged in, redirect them to their profile page
  React.useEffect(() => {
    if (currentUser?.name) {
      navigate(`/user/${currentUser.name}`);
    }
  }, [currentUser, navigate]);

  return (
    <div role="main" className="text-center">
      <Helmet>
        <title>Sign in</title>
      </Helmet>
      <h2 className="page-title">Sign in</h2>

      <p>
        To sign in, use your MusicBrainz account, and authorize ListenBrainz to
        access your profile data.
      </p>

      <div className="well" style={{ maxWidth: "600px", margin: "0 auto" }}>
        <p className="text-danger" style={{ fontSize: "16pt" }}>
          Important!
        </p>
        <p>
          By signing into ListenBrainz, you grant the MetaBrainz Foundation
          permission to include your listening history in data dumps we make
          publicly available under the{" "}
          <a href="https://creativecommons.org/publicdomain/zero/1.0/">
            CC0 license
          </a>
          . None of your private information from your user profile will be
          included in these data dumps.
        </p>
        <p>
          Furthermore, you grant the MetaBrainz Foundation permission to process
          your listening history and include it in new open source tools such as
          recommendation engines that the ListenBrainz project is building. For
          details on processing your listening history, please see our{" "}
          <a href="https://metabrainz.org/gdpr">GDPR compliance statement</a>.
        </p>
        <p>
          In order to combat spammers and to be able to contact our users in
          case something goes wrong with the listen submission process, we now
          require an email address when creating a ListenBrainz account.
        </p>
        <p>
          If after creating an account you change your mind about processing
          your listening history, you will need to{" "}
          <Link to="/settings/delete/">delete your ListenBrainz account</Link>.
        </p>
      </div>
      <br />
      <div className="well" style={{ maxWidth: "600px", margin: "0 auto" }}>
        <a
          href={`/login/musicbrainz/${next ? `?next=${next}` : ""}`}
          className="btn btn-primary btn-lg btn-block"
        >
          Sign in with MusicBrainz
        </a>
      </div>
    </div>
  );
}
