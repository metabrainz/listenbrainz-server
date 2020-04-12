import * as ReactDOM from "react-dom";
import * as React from "react";
import Importer from "./Importer";

import LastFMImporterModal from "./LastFMImporterModal";

export interface ImporterProps {
  user: {
    id?: string;
    name: string;
    auth_token: string;
  };
  profileUrl?: string;
  apiUrl?: string;
  lastfmApiUrl: string;
  lastfmApiKey: string;
}

export interface ImporterState {
  show: boolean;
  canClose: boolean;
  lastfmUsername: string;
  msg: string;
}

export default class LastFmImporter extends React.Component<
  ImporterProps,
  ImporterState
> {
  importer: any;

  constructor(props: ImporterProps) {
    super(props);

    this.state = {
      show: false,
      canClose: true,
      lastfmUsername: "",
      msg: "",
    };
  }

  handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState({ lastfmUsername: event.target.value });
  };

  handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    const { lastfmUsername } = this.state;
    this.toggleModal();
    event.preventDefault();
    this.importer = new Importer(lastfmUsername, this.props);
    setInterval(this.updateMessage, 100);
    setInterval(this.setClose, 100);
    this.importer.startImport();
  };

  toggleModal = () => {
    this.setState((prevState) => {
      return { show: !prevState.show };
    });
  };

  setClose = () => {
    this.setState({ canClose: this.importer.canClose });
  };

  updateMessage = () => {
    this.setState({ msg: this.importer.msg });
  };

  render() {
    const { show, canClose, lastfmUsername, msg } = this.state;

    return (
      <div className="Importer">
        <form onSubmit={this.handleSubmit}>
          <input
            type="text"
            onChange={this.handleChange}
            value={lastfmUsername}
            placeholder="Last.fm Username"
            size={30}
          />
          <input type="submit" value="Import Now!" disabled={!lastfmUsername} />
        </form>
        {show && (
          <LastFMImporterModal onClose={this.toggleModal} disable={!canClose}>
            <img
              src="/static/img/listenbrainz-logo.svg"
              height="75"
              className="img-responsive"
              alt=""
            />
            <br />
            <br />
            <div>{msg}</div>
            <br />
          </LastFMImporterModal>
        )}
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#react-container");
  const propsElement = document.getElementById("react-props");
  let reactProps;
  try {
    reactProps = JSON.parse(propsElement!.innerHTML);
  } catch (err) {
    // Show error to the user and ask to reload page
  }
  const {
    user,
    profile_url,
    api_url,
    lastfm_api_url,
    lastfm_api_key,
  } = reactProps;
  ReactDOM.render(
    <LastFmImporter
      user={user}
      profileUrl={profile_url}
      apiUrl={api_url}
      lastfmApiKey={lastfm_api_key}
      lastfmApiUrl={lastfm_api_url}
    />,
    domContainer
  );
});
