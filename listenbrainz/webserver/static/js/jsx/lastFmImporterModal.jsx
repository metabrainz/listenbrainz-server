'use strict'

import React from 'react';
import ReactDOM from 'react-dom';
import Importer from './importer'
import { faTimes } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

class Modal extends React.Component {
  render() {
    if (!this.props.show) {
      return null;
    }
    const divStyle = {
      position: 'fixed', 
      top: '200px', 
      zIndex: '200000000000000', 
      width: '500px', 
      marginLeft: '-250px', 
      left: '50%', 
      backgroundColor: '#fff',
      boxShadow: '0 19px 38px rgba(0,0,0,0.30), 0 15px 12px rgba(0,0,0,0.22)',
      textAlign: 'center', 
      padding:'50px',
    };
    
    const buttonStyle = {
      position: 'absolute',
      top: '5px',
      right: '10px',
      outline: 'none',
      border: 'none',
      background: 'transparent',
    };
    return (
      <div style={divStyle} id="listen-progress-container">
      <button onClick={this.props.onClose} style={buttonStyle} disabled={this.props.disable}>
      <FontAwesomeIcon icon={faTimes} />
      </button>
      <div>
      {this.props.children}
      </div>
      </div>
      );
    }
  }
  
  class App extends React.Component {
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
      ReactDOM.render(<App {...reactProps}/>, domContainer);
    });