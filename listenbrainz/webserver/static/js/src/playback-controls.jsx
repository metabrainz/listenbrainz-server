// TODO: Port to typescript

import { faEye, faEyeSlash, faFastBackward, faFastForward, faPauseCircle, faPlayCircle, faSortAmountDown, faSortAmountUp } from '@fortawesome/free-solid-svg-icons'

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import React from 'react';
function millisecondsToHumanReadable(milliseconds) {
  var seconds = milliseconds / 1000;
  var numyears = Math.floor(seconds / 31536000);
  var numdays = Math.floor((seconds % 31536000) / 86400);
  var numhours = Math.floor(((seconds % 31536000) % 86400) / 3600);
  var numminutes = Math.floor((((seconds % 31536000) % 86400) % 3600) / 60);
  var numseconds = Math.floor((((seconds % 31536000) % 86400) % 3600) % 60);
  var string = "";
  if (numyears) string += numyears + " y ";
  if (numdays) string += numdays + " d ";
  if (numhours) string += numhours + " h ";
  if (numminutes) string += numminutes + " m ";
  if (numseconds) string += numseconds + " s";

  return string;
}

export class PlaybackControls extends React.Component {

  state = {
    autoHideControls: true
  }

  render() {
    return (
      <div id="music-player" aria-label="Playback control">
        <div className="album">
          {this.props.children ? this.props.children :
            <div className="noAlbumArt">No album art</div>}
        </div>
        <div className={`info ${!this.state.autoHideControls || !this.props.children || this.props.playerPaused ? 'showControls' : ''}`}>
          <div className="currently-playing">
            <h2 className="song-name">{this.props.trackName || '—'}</h2>
            <h3 className="artist-name">{this.props.artistName}</h3>
            <div className="progress">
              <div className="progress-bar" style={{ width: `${this.props.progress_ms * 100 / this.props.duration_ms}%` }}></div>
            </div>
          </div>
          <div className="controls">
            <div className="left btn btn-xs"
              title={`${this.state.autoHideControls ? 'Always show' : 'Autohide'} controls`}
              onClick={() => this.setState(state => ({ autoHideControls: !state.autoHideControls }))}>
                <FontAwesomeIcon icon={this.state.autoHideControls ? faEyeSlash : faEye}/>
            </div>
            <div className="previous btn btn-xs" onClick={this.props.playPreviousTrack} title="Previous">
              <FontAwesomeIcon icon={faFastBackward}/>
            </div>
            <div className="play btn" onClick={this.props.togglePlay} title={`${this.props.playerPaused ? 'Play' : 'Pause'}`} >
              <FontAwesomeIcon icon={this.props.playerPaused ? faPlayCircle : faPauseCircle} size="2x"/>
            </div>
            <div className="next btn btn-xs" onClick={this.props.playNextTrack} title="Next">
              <FontAwesomeIcon icon={faFastForward}/>
            </div>
            {this.props.direction !== "hidden" &&
              <div className="right btn btn-xs" onClick={this.props.toggleDirection} title={`Play ${this.props.direction === 'up' ? 'down' : 'up'}`}>
                <FontAwesomeIcon icon={this.props.direction === 'up' ? faSortAmountUp : faSortAmountDown}/>
              </div>
            }
          </div>
        </div>
      </div>
    );
  }
}
