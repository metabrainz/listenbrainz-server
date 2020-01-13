'use strict'

import React from 'react';
import ReactDOM from 'react-dom';
import Modal from './modal.jsx'

class Importer extends React.Component {
  constructor(props) {
    super(props);

     this.state = {
      show: false,
      username: '',
    };

    this.handleChange = this.handleChange.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);
    this.toggleModal = this.toggleModal.bind(this)
  }

  handleChange(event) {
    this.setState({username: event.target.value});
  } 

  handleSubmit(event) {
    this.toggleModal();
    event.preventDefault();
  }

  toggleModal() {
    this.setState((prevState) => {
      return {show: !prevState.show}
    });
  }

  render() {
    return (
      <div className="Importer">
        <form onSubmit={this.handleSubmit}>
          <input type="text" onChange={this.handleChange} value={this.state.username} placeholder="Last.fm Username" size="30" />
          <input type="submit" value="Import Now!" disabled={!this.state.username}/>
        </form>
        <Modal show={this.state.show} onClose={this.toggleModal}> 
          <img src='/static/img/listenbrainz-logo.svg' height='75' />
          <p>Status updates go here</p>
        </Modal>
      </div>
    );
  }
}

const domContainer = document.querySelector("#react-container");
ReactDOM.render(<Importer />, domContainer);