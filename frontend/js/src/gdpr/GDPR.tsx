import * as React from "react";
import { Helmet } from "react-helmet";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

export default function GDPR() {
  const next = new URLSearchParams(window.location.search).get("next");
  const navigate = useNavigate();
  const location = useLocation();

  const onFormSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const gdprOption = formData.get("gdpr-options");
    if (gdprOption === "agree") {
      try {
        const response = await fetch(location.pathname, {
          method: "POST",
          body: formData,
        });
        if (response.ok) {
          if (next) {
            navigate(next);
          } else {
            navigate("/");
          }
        }
      } catch (error) {
        toast.error("An error occurred while processing your request.");
      }
    }
    if (gdprOption === "disagree") {
      navigate("/settings/delete/");
    }
  };

  return (
    <div role="main">
      <Helmet>
        <title>Agree to Terms</title>
      </Helmet>
      <h2 className="page-title">
        Agree to General Data Protection Regulations
      </h2>
      <form onSubmit={onFormSubmit}>
        <div
          className="well bg-danger"
          style={{ maxWidth: "600px", margin: "0 auto" }}
        >
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
            Furthermore, you grant the MetaBrainz Foundation permission to
            process your listening history and include it in new open source
            tools such as recommendation engines that the ListenBrainz project
            is building. For details on processing your listening history,
            please see our{" "}
            <a href="https://metabrainz.org/gdpr">GDPR compliance statement</a>.
          </p>
          <p>
            If you change your mind about processing your listening history, you
            will need to{" "}
            <a href="/login/musicbrainz">delete your ListenBrainz account</a>.
          </p>
          <input
            type="radio"
            id="gdpr-agree"
            name="gdpr-options"
            value="agree"
            required
          />{" "}
          <label htmlFor="gdpr-agree"> OK, I agree</label>
          <br />
          <input
            type="radio"
            id="gdpr-disagree"
            name="gdpr-options"
            value="disagree"
            required
          />{" "}
          <label htmlFor="gdpr-disagree">
            No, take me to the account deletion page
          </label>
          <br />
          {next && <input type="hidden" name="next" value={next} />}
        </div>
        <br />
        <div className="well" style={{ maxWidth: "600px", margin: "0 auto" }}>
          <button type="submit" className="btn btn-primary btn-lg btn-block">
            Submit choice!
          </button>
        </div>
      </form>
    </div>
  );
}
