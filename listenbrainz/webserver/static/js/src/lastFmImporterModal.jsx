// TODO: Port to typescript

import React from 'react';
import { faTimes } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

export default class Modal extends React.Component {
  render() {
    const divStyle = {
      position: 'fixed',
      height: '90%',
      maxHeight: '300px',
      top: '50%',
      zIndex: '200000000000000',
      width: '90%',
      maxWidth: '500px',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      backgroundColor: '#fff',
      boxShadow: '0 19px 38px rgba(0,0,0,0.30), 0 15px 12px rgba(0,0,0,0.22)',
      textAlign: 'center',
      padding: '50px',
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
