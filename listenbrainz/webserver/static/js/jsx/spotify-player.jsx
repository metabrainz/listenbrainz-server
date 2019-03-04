import * as _isEqual from 'lodash.isequal';

import {PlaybackControls} from './playback-controls.jsx';
import React from 'react';

function getSpotifyUriFromListen(listen) {
  if (!listen || !listen.track_metadata || !listen.track_metadata.additional_info ||
      typeof listen.track_metadata.additional_info.spotify_id !== "string")
  {
      return null;
  }
  const spotifyId = listen.track_metadata.additional_info.spotify_id;
  const spotify_track = spotifyId.split('https://open.spotify.com/')[1];
  if (typeof spotify_track !== "string")
  {
      return null;
  }
  return "spotify:" + spotify_track.replace("/", ":");
}

export class SpotifyPlayer extends React.Component {

  _spotifyPlayer;
  _firstRun = true;

  constructor(props) {
    super(props);
    this.state = {
      accessToken: props.spotify_access_token,
      currentSpotifyTrack: null,
      playerPaused: true,
      errorMessage: null,
      warningMessage: null,
      progressMs: 0,
      durationMs: 0,
      direction: props.direction || "down"
    };
    this.playNextTrack = this.playNextTrack.bind(this);
    this.playPreviousTrack = this.playPreviousTrack.bind(this);
    this.togglePlay = this.togglePlay.bind(this);
    this.toggleDirection = this.toggleDirection.bind(this);
    this.handlePlayerStateChanged = this.handlePlayerStateChanged.bind(this);
    this.handleSpotifyAPICurrentlyPlaying = this.handleSpotifyAPICurrentlyPlaying.bind(this);
    this.handleError = this.handleError.bind(this);
    this.isCurrentListen = this.isCurrentListen.bind(this);
    this.getAlbumArt = this.getAlbumArt.bind(this);
    this.playListen = this.playListen.bind(this);
    this.disconnectSpotifyPlayer = this.disconnectSpotifyPlayer.bind(this);
    this.connectSpotifyPlayer = this.connectSpotifyPlayer.bind(this);
    window.onSpotifyWebPlaybackSDKReady = this.connectSpotifyPlayer;
    const spotifyPlayerSDKLib = require('../lib/spotify-player-sdk-1.6.0');
  }

  play_spotify_uri(spotify_uri) {
    if (!this._spotifyPlayer)
    {
      const error = "Spotify player not initialized. Please refresh the page";
      this.setState({ errorMessage: error });
      return;
    }
    fetch(`https://api.spotify.com/v1/me/player/play?device_id=${this._spotifyPlayer._options.id}`, {
      method: 'PUT',
      body: JSON.stringify({ uris: [spotify_uri] }),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.state.accessToken}`
      },
    })
    .then(response =>{
      if(response.status === 403 || response.status === 401){
        return this.handleAccountError(response.statusText);
      }
      if(!response.ok){
        return this.handleError(response.statusText);
      }
      return;
    })
    .catch(this.handleError);
  };

  playListen(listen) {
    if (listen.track_metadata.additional_info.spotify_id)
    {
      this.play_spotify_uri(getSpotifyUriFromListen(listen));
      this.props.onCurrentListenChange(listen);
    } else
    {
      console.error("No Spotify ID for this listen :/");
      this.handleError("Cannot play this song on Spotify");
    }
  };
  isCurrentListen(element) {
    return this.props.currentListen
      && _isEqual(element,this.props.currentListen);
  }
  playPreviousTrack() {
    this.playNextTrack(true);
  }
  playNextTrack(invert) {
    if (this.props.listens.length === 0)
    {
      const error = "No Spotify listens to play. Maybe refresh the page?";
      console.error(error);
      this.setState({ errorMessage: error });
      return;
    }

    const currentListenIndex = this.props.listens.findIndex(this.isCurrentListen);

    let nextListenIndex;
    if (currentListenIndex === -1)
    {
      nextListenIndex = this.state.direction === "up" ? this.props.listens.length - 1 : 0;
    }
    else if (this.state.direction === "up")
    {
      nextListenIndex = invert === true ? currentListenIndex + 1 : (currentListenIndex - 1 || 0);
    }
    else if (this.state.direction === "down")
    {
      nextListenIndex = invert === true ? (currentListenIndex - 1 || 0) : currentListenIndex + 1;
    }
    else {
      const warning = "Unrecognised state. Please select a song to play.";
      console.warning(warning);
      this.setState({ warningMessage: warning });
      return;
    }
    
    const nextListen = this.props.listens[nextListenIndex];
    if (!nextListen)
    {
      const error = "No more listens, maybe wait some?";
      console.error(error);
      this.setState({ errorMessage: error });
      return;
    }

    this.playListen(nextListen);
    this.handleError(null);
  }
  handleError(error) {
    if (!error)
    {
      this.setState({ errorMessage: null });
      return;
    }
    console.error(error);
    error = error.message ? error.message : error;
    this.setState({ errorMessage: error });
  }

  handleAccountError(error) {
    const errorMessage = 'Failed to validate Spotify premium account';
    console.error(errorMessage, error);
    this.setState({ accessToken: null, errorMessage });
    if(typeof this.props.onAccountError === "function") {
      this.props.onAccountError(error);
    }
  }

  async togglePlay() {
    try
    {
      await this._spotifyPlayer.togglePlay();
    } catch (error)
    {
      this.handleError(error);
    }
  }

  toggleDirection() {
    this.setState(prevState => {
      const direction = prevState.direction === "down" ? "up" : "down";
      return { direction: direction }
    });
  }
  disconnectSpotifyPlayer() {
    if (!this._spotifyPlayer)
    {
      return;
    }
    if (typeof this._spotifyPlayer.disconnect === "function")
    {
      this._spotifyPlayer.disconnect();
      this._spotifyPlayer.removeListener('initialization_error');
      this._spotifyPlayer.removeListener('authentication_error');
      this._spotifyPlayer.removeListener('account_error');
      this._spotifyPlayer.removeListener('playback_error');
      this._spotifyPlayer.removeListener('ready');
      this._spotifyPlayer.removeListener('player_state_changed');
    }
    this._spotifyPlayer = null;
    this.handleError(null);
    this._firstRun = true;
  }

  connectSpotifyPlayer() {
    this.disconnectSpotifyPlayer();
    if (!this.state.accessToken)
    {
      console.error("No spotify acces_token");
      const noTokenErrorMessage = <span>No Spotify access token. Please try to <a href="/profile/connect-spotify">link your account</a> and refresh this page</span>;
      this.handleError(noTokenErrorMessage);
      return;
    }

    this._spotifyPlayer = new window.Spotify.Player({
      name: 'ListenBrainz Player',
      getOAuthToken: callback => {
        callback(this.state.accessToken);
      },
      volume: 0.7 // Careful with this, now…
    });

    // Error handling
    const authErrorMessage = <span>Spotify authentication error. <br /><button onClick={this.connectSpotifyPlayer} className="btn btn-primary">Reconnect</button> or <a href="/profile/connect-spotify">relink your Spotify account</a></span>
    this._spotifyPlayer.on('initialization_error', this.handleError);
    this._spotifyPlayer.on('authentication_error', error => this.handleError(authErrorMessage));
    this._spotifyPlayer.on('account_error', this.handleAccountError);
    this._spotifyPlayer.on('playback_error', this.handleError);

    this._spotifyPlayer.addListener('ready', ({ device_id }) => {
      console.log('Spotify player connected with Device ID', device_id);
      this.handleError(null);
    });

    this._spotifyPlayer.addListener('player_state_changed', this.handlePlayerStateChanged);

    this._spotifyPlayer.connect().then(success => {
      if (success)
      {
        console.log('The Web Playback SDK successfully connected to Spotify!');
        this.handleError(null);
        return fetch('https://api.spotify.com/v1/me/player/currently-playing', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.state.accessToken}`
          },
        });
      }
      else
      {
        throw Error('Could not connect Web Playback SDK');
      }
    })
    .then(response => {
      if(response.status === 202 || response.status === 204)
      {
        // Failure, no response body.
        return;
      }
      return response.json().then(response => {
        if (response.error) {
          return this.handleError(response.error.message)
        }
        this.handleSpotifyAPICurrentlyPlaying(response);
      })
    })
    .catch(this.handleError);
  }

  handleSpotifyAPICurrentlyPlaying(currentlyPlaying) {
    this.setState({
      progressMs: currentlyPlaying.progress_ms,
      durationMs: currentlyPlaying.item && currentlyPlaying.item.duration_ms,
      currentSpotifyTrack: currentlyPlaying.item,
      errorMessage: null,
      warningMessage: currentlyPlaying.is_playing ? 'Using Spotify on this page will interrupt your current playback' : ''
    });
  }

  handlePlayerStateChanged({
    paused,
    position,
    duration,
    track_window: { current_track }
  }) {
    console.debug('Currently Playing', current_track);
    console.debug('Position in Song', position);
    console.debug('Duration of Song', duration);
    console.debug('Player paused?', paused);

    // How do we accurately detect the end of a song?
    if (position === 0 && paused === true)
    {
      // Track finished, play next track
      console.debug("Detected Spotify end of track, playing next track")
      this.playNextTrack();
      return;
    }
    this.setState({
      progressMs: position,
      durationMs: duration,
      currentSpotifyTrack: current_track,
      playerPaused: paused,
      errorMessage: null
    });
    if (this._firstRun)
    {
      this._firstRun = false;
    }
  }

  getAlbumArt() {
    const track = this.state.currentSpotifyTrack;
    if (!track || !track.album || !Array.isArray(track.album.images))
    {
      return null
    }
    const sortedImages = track.album.images.sort((a, b) => a.height > b.height ? -1 : 1);
    return sortedImages[0] && <img className="img-responsive" src={sortedImages[0].url} />;
  }

  render() {
    return (
      <div>
        <PlaybackControls
          playPreviousTrack={this.playPreviousTrack}
          playNextTrack={this.playNextTrack}
          togglePlay={this._firstRun ? this.playNextTrack : this.togglePlay}
          playerPaused={this.state.playerPaused}
          toggleDirection={this.toggleDirection}
          direction={this.state.direction}
          trackName={this.state.currentSpotifyTrack && this.state.currentSpotifyTrack.name}
          artistName={this.state.currentSpotifyTrack &&
            this.state.currentSpotifyTrack.artists.map(artist => artist.name).join(', ')
          }
          progress_ms={this.state.progressMs}
          duration_ms={this.state.durationMs}
        >
          {this.getAlbumArt()}
        </PlaybackControls>

        {this.state.errorMessage &&
          <div className="alert alert-danger" role="alert">
            {this.state.errorMessage}
          </div>
        }
        {this.state.warningMessage &&
          <div className="alert alert-warning" role="alert">
            {this.state.warningMessage}
          </div>
        }
      </div>
    );
  }
}
