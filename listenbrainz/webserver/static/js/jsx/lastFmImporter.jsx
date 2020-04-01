'use strict'

import React from 'react';
import ReactDOM from 'react-dom';
import Importer from './importer'
import Modal from './lastFmImporterModal.jsx'


export default class LastFmImporter extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      show: false,
      canClose: true,
      lastfmUsername: '',
      msg: '',
    };
  }

  handleChange = (event) => {
    this.setState({ lastfmUsername: event.target.value });
  }

  handleSubmit = (event) => {
    this.toggleModal();
    event.preventDefault();
    this.importer = new Importer(this.state.lastfmUsername, this.props);
    setInterval(this.updateMessage, 100);
    setInterval(this.setClose, 100);
    this.importer.startImport()
  }

  toggleModal = () => {
    this.setState((prevState) => {
      return { show: !prevState.show };
    });
  }

  setClose = () => {
    this.setState({ canClose: this.importer.canClose });
  }

  updateMessage = () => {
    this.setState({ msg: this.importer.msg });
  }

  render() {
    return (
      <div className="Importer">
        <form onSubmit={this.handleSubmit}>
          <input type="text" onChange={this.handleChange} value={this.state.lastfmUsername} placeholder="Last.fm Username" size="30" />
          <input type="submit" value="Import Now!" disabled={!this.state.lastfmUsername} />
        </form>
        {this.state.show &&
          <Modal onClose={this.toggleModal} disable={!this.state.canClose}>
            <img src='/static/img/listenbrainz-logo.svg' height='75' className='img-responsive'/>
            <br /><br />
            <div>{this.state.msg}</div>
            <br />
          </Modal>
        }
      </div>
    );
  }
}

document.addEventListener('DOMContentLoaded', (event) => {
  let domContainer = document.querySelector("#react-container");
  let propsElement = document.getElementById('react-props');
  let reactProps;
  try {
    reactProps = JSON.parse(propsElement.innerHTML);
  }
  catch (err) {
    console.error("Error parsing props:", err);
  }
  ReactDOM.render(<LastFmImporter {...reactProps} />, domContainer);
});
