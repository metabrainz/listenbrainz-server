import * as React from "react";
import { useSearchParams } from "react-router-dom";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../../utils/GlobalAppContext";

export default function APIAuth() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const userName = currentUser?.name;
  const [message, setMessage] = React.useState<string | null>(null);
  const token = searchParams.get("token");
  if (!token) {
    return (
      <div role="main">
        <h2 className="page-title">Invalid token</h2>
        <p>
          The token is missing in the request. Please try again with a valid
          token.
        </p>
      </div>
    );
  }

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const respose = await fetch("/api/auth/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ token }),
    });

    const data = await respose.json();
    const { message: responseMessage } = data;

    setMessage(responseMessage);
  };

  return (
    <div role="main">
      <Helmet>
        <title>User &quot;{userName}&quot;</title>
      </Helmet>
      <h2 className="page-title">{userName}</h2>

      {message || (
        <>
          <h3>
            Approve this client for account <b>{userName}</b>?
          </h3>
          <p>
            A legacy last.fm application wishes to have access to your account.
            If you approve it, this application will be able to submit listens
            on your behalf. Please consider asking the developers of your
            application to add support to submit directly to ListenBrainz.
          </p>
          Allow access?
          <br />
          <form onSubmit={onSubmit}>
            <input type="hidden" name="token" value={token} />
            <input type="submit" value="Yes please" />
          </form>
        </>
      )}
    </div>
  );
}
