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
              <span className={`${this.state.autoHideControls ? 'hidden' : ''}`}>
                <i className="fas fa-eye"></i>
              </span>
              <span className={`${!this.state.autoHideControls ? 'hidden' : ''}`}>
                <i className="fas fa-eye-slash"></i>
              </span>
            </div>
            <div className="previous btn btn-xs" onClick={this.props.playPreviousTrack} title="Previous">
              <i className="fas fa-fast-backward"></i>
            </div>
            <div className="play btn" onClick={this.props.togglePlay} title={`${this.props.playerPaused ? 'Play' : 'Pause'}`} >
              <span className={`${this.props.playerPaused ? 'hidden' : ''}`}>
                <i className="fa fa-2x fa-pause-circle"></i>
              </span>
              <span className={`${!this.props.playerPaused ? 'hidden' : ''}`}>
                <i className="fa fa-2x fa-play-circle"></i>
              </span>
            </div>
            <div className="next btn btn-xs" onClick={this.props.playNextTrack} title="Next">
              <i className="fas fa-fast-forward"></i>
            </div>
            {this.props.direction !== "hidden" &&
              <div className="right btn btn-xs" onClick={this.props.toggleDirection} title={`Play ${this.props.direction === 'up' ? 'down' : 'up'}`}>
                <span className={`${this.props.direction === 'up' ? 'hidden' : ''}`}>
                  <i className="fa fa-sort-amount-down"></i>
                </span>
                <span className={`${this.props.direction === 'down' ? 'hidden' : ''}`}>
                  <i className="fa fa-sort-amount-up"></i>
                </span>
              </div>
            }
          </div>
        </div>
      </div>
    );
  }
}