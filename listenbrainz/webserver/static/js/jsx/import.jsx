'use strict'

import React from 'react';
import ReactDOM from 'react-dom';
import Modal from './modal.jsx';

class Importer extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      show: false,
      canClose: true,
      lastfmUsername: '',
      msg: '',
    };

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.toggleModal = this.toggleModal.bind(this);
    this.getTotalNumberOfScrobbles = this.getTotalNumberOfScrobbles.bind(this);

    this.userName = props.user.name;
    this.lastfmURL = props.lastfm_api_url;
    this.lastfmKey = props.lastfm_api_key;
    this.playCount = -1; // the number of scrobbles reported by Last.FM
  }

  handleChange(event) {
    this.setState({lastfmUsername: event.target.value});
  } 

  handleSubmit(event) {
    this.toggleModal();
    this.setState({canClose: false}); // Disable the close button
    this.updateMessage("Your import from Last.fm is starting!");
    this.getTotalNumberOfScrobbles();
    event.preventDefault();
  }

  toggleModal() {
    this.setState((prevState) => {
      return {show: !prevState.show};
    });
  }

  updateMessage(msg) {
    this.setState({msg: msg});
  }

  async getTotalNumberOfScrobbles() {
    /*
     * Get the total play count reported by Last.FM for user
     */

    let url = this.lastfmURL + '?method=user.getinfo&user=' + this.state.lastfmUsername + '&api_key=' + this.lastfmKey + '&format=json';
    try {
      let response = await fetch(encodeURI(url));
      let data = await response.json();
      if ('playcount' in data['user']) {
        this.playCount = parseInt(data['user']['playcount']);
      } else {
        this.playCount = -1;
      }
      this.updateMessage(this.playCount);
    } catch {
      this.updateMessage("An error occurred, please try again. :(")
      this.setState({canClose: true}); // Enable the close button
    }
  } 

  render() {
    return (
      <div className="Importer">
        <form onSubmit={this.handleSubmit}>
          <input type="text" onChange={this.handleChange} value={this.state.lastfmUsername} placeholder="Last.fm Username" size="30" />
          <input type="submit" value="Import Now!" disabled={!this.state.lastfmUsername}/>
        </form>
        <Modal show={this.state.show} onClose={this.toggleModal} disable={!this.state.canClose}> 
          <img src='/static/img/listenbrainz-logo.svg' height='75' />
          <br/><br/>
          <p>{this.state.msg}</p>
        </Modal>
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
  ReactDOM.render(<Importer {...reactProps}/>, domContainer);
});