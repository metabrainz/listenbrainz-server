'use strict'

import React from 'react';
import ReactDOM from 'react-dom';
import Importer from './importer'
import Modal from './lastFmImporterModal.jsx'

  
class LastFmImporter extends React.Component {
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
    this.setState({lastfmUsername: event.target.value});
  } 
  
  handleSubmit = (event) => {
    this.toggleModal();
    event.preventDefault();
    this.importer = new Importer(this.state.lastfmUsername, this.props, this.updateMessage, this.setClose);
    this.importer.startImport();
  }
  
  toggleModal = () => {
    this.setState((prevState) => {
      return {show: !prevState.show};
    });
  }
  
  setClose = (value) => {
    this.setState({canClose: value});
  }
  
  updateMessage = (msg) => {
    this.setState({msg: msg});
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
          <div>{this.state.msg}</div>
          <br/>
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
  ReactDOM.render(<LastFmImporter {...reactProps}/>, domContainer);
});