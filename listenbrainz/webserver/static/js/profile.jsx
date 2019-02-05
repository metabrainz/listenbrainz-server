'use strict';

function getSpotifyEmbedUriFromListen(listen) {

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
  return spotifyId.replace("https://open.spotify.com/", "https://open.spotify.com/embed/");
}

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

function getArtistLink(listen) {
  if (listen.track_metadata.additional_info.artist_mbids && listen.track_metadata.additional_info.artist_mbids.length)
  {
    return (<a href={`http://musicbrainz.org/artist/${listen.track_metadata.additional_info.artist_mbids[0]}`}>
      {listen.track_metadata.artist_name}
    </a>);
  }
  return listen.track_metadata.artist_name
}

function getTrackLink(listen) {
  if (listen.track_metadata.additional_info.recording_mbid)
  {
    return (<a href={`http://musicbrainz.org/recording/${listen.track_metadata.additional_info.recording_mbid}`}>
      {listen.track_metadata.track_name}
    </a>);
  }
  return listen.track_metadata.track_name;
}

function getPlayButton(listen, onClickFunction) {
  if (listen.track_metadata.additional_info.spotify_id)
  {
    return (
      <button title="Play" className="btn btn-link" onClick={onClickFunction.bind(listen)}>
        <i className="fas fa-play-circle fa-2x"></i>
      </button>
    )
  }
  return null;
}

class PlaybackControls extends React.Component {

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
            <div class="progress">
              <div class="progress-bar" style={{ width: `${this.props.progress_ms * 100 / this.props.duration_ms}%` }}></div>
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

class SpotifyPlayer extends React.Component {

  _spotifyPlayer;
  _accessToken;
  _firstRun = true;

  constructor(props) {
    super(props);
    this.state = {
      listens: props.listens,
      currentSpotifyTrack: null,
      playerPaused: true,
      errorMessage: null,
      warningMessage: null,
      progressMs: 0,
      durationMs: 0,
      direction: props.direction || "down"
    };
    this._accessToken = props.spotify_access_token;
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
        'Authorization': `Bearer ${this._accessToken}`
      },
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
      && element.listened_at
      && element.listened_at === this.props.currentListen.listened_at;
  }
  playPreviousTrack() {
    this.playNextTrack(true);
  }
  playNextTrack(invert) {
    if (this.state.listens.length === 0)
    {
      const error = "No Spotify listens to play. Maybe refresh the page?";
      console.error(error);
      this.setState({ errorMessage: error });
      return;
    }

    const currentListenIndex = this.state.listens.findIndex(this.isCurrentListen);
    let nextListen;
    if (currentListenIndex === -1)
    {
      nextListen = this.state.direction === "up" ? this.state.listens[this.state.listens.length - 1] : this.state.listens[0];
    }
    else if ((this.state.direction === "up" && invert !== true) || invert === true)
    {
      nextListen = this.state.listens[currentListenIndex - 1];
    } else
    {
      nextListen = this.state.listens[currentListenIndex + 1];
    }

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
    if (!this._accessToken)
    {
      console.error("No spotify acces_token");
      const noTokenErrorMessage = <span>No Spotify access token. Please try to <a href="/profile/connect-spotify">link your account</a> and refresh this page</span>;
      this.handleError(noTokenErrorMessage);
      return;
    }

    this._spotifyPlayer = new window.Spotify.Player({
      name: 'ListenBrainz Player',
      getOAuthToken: callback => {
        callback(this._accessToken);
      },
      volume: 0.7 // Careful with this, now…
    });

    // Error handling
    const authErrorMessage = <span>Spotify authentication error. <br /><button onClick={this.connectSpotifyPlayer} className="btn btn-primary">Reconnect</button> or <a href="/profile/connect-spotify">relink your Spotify account</a></span>
    this._spotifyPlayer.on('initialization_error', this.handleError);
    this._spotifyPlayer.on('authentication_error', error => this.handleError(authErrorMessage));
    this._spotifyPlayer.on('account_error', this.handleError);
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
        fetch('https://api.spotify.com/v1/me/player/currently-playing', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this._accessToken}`
          },
        })
        .then(response => response.json())
        .then(this.handleSpotifyAPICurrentlyPlaying)
        .catch(this.handleError);
      }
      else
      {
        this.handleError('Could not connect Web Playback SDK');
      }
    });
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



class RecentListens extends React.Component {

  spotifyListens = [];
  constructor(props) {
    super(props);
    this.state = {
      listens: props.listens || [],
      currentListen: null,
      mode: props.mode === "follow" ? "follow" : "listens",
      playingNowByUser: {}
    };
    this.isCurrentListen = this.isCurrentListen.bind(this);
    this.handleCurrentListenChange = this.handleCurrentListenChange.bind(this);
    this.playListen = this.playListen.bind(this);
    this.spotifyPlayer = React.createRef();
    window.handleIncomingListen = this.receiveNewListen.bind(this);
    window.handleIncomingPlayingNow = this.receiveNewPlayingNow.bind(this);
  }

  playListen(listen) {
    if (this.spotifyPlayer.current)
    {
      this.spotifyPlayer.current.playListen(listen);
      return;
    } else
    {
      // For fallback embedded player
      this.setState({ currentListen: listen });
      return;
    }
  }

  receiveNewListen(newListen) {
    try
    {
      newListen = JSON.parse(newListen);
    } catch (error)
    {
      console.error(error);
    }
    console.debug(typeof newListen, newListen);
    this.setState(prevState => {
      return { listens: [newListen].concat(prevState.listens) }
    })
  }
  receiveNewPlayingNow(newPlayingNow) {
    try
    {
      newPlayingNow = JSON.parse(newPlayingNow);
    } catch (error)
    {
      console.error(error);
    }
    newPlayingNow.playing_now = true;

    this.setState(prevState => {
      if (prevState.mode === "follow")
      {
        const userName = newPlayingNow.user_name;
        return {
          playingNowByUser: Object.assign(
            {},
            prevState.playingNowByUser,
            { [userName]: newPlayingNow }
          )
        }
      }
      const indexOfPreviousPlayingNow = prevState.listens.findIndex(listen => listen.playing_now);
      prevState.listens.splice(indexOfPreviousPlayingNow, 1);
      return { listens: [newPlayingNow].concat(prevState.listens) }
    })
  }

  handleCurrentListenChange(listen) {
    this.setState({ currentListen: listen });
  }
  isCurrentListen(listen) {
    return this.state.currentListen && this.state.currentListen.listened_at === listen.listened_at;
  }
  handleFollowUserListChange(users) {
    if (!Array.isArray(users))
    {
      console.error("Expected array in handleFollowUserListChange, got", typeof users);
      return;
    }
    if (typeof window.emitFollowUsersList !== "function")
    {
      console.error("window.emitFollowUsersList is not a function, can't emit follow users list");
      return;
    }
    window.emitFollowUsersList(users);
  }

  render() {

    const spotifyListens = this.state.listens.filter(listen => listen.track_metadata
      && listen.track_metadata.additional_info
      && listen.track_metadata.additional_info.listening_from === "spotify"
    );

    const getSpotifyEmbedSrc = () => {
      if (this.state.currentListen)
      {
        return getSpotifyEmbedUriFromListen(this.state.currentListen);
      } else if (spotifyListens.length)
      {

        return getSpotifyEmbedUriFromListen(spotifyListens[0]);
      }
      return null
    };

    return (
      <div>
        {this.state.mode === "listens" && <div className="row">
          <div className="col-md-8">
            <h3> Statistics </h3>
            <table className="table table-border table-condensed table-striped">
              <tbody>
                {this.props.listen_count &&
                  <tr>
                    <td>Listen count</td>
                    <td>{this.props.listen_count}</td>
                  </tr>
                }
                {this.props.artist_count &&
                  <tr>
                    <td>Artist count</td>
                    <td>{this.props.artist_count}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
        }
        {this.state.mode === "follow" &&
          <FollowUsers onUserListChange={this.handleFollowUserListChange}
            initialList={this.props.follow_list} playListen={this.playListen.bind(this)}
            playingNow={this.state.playingNowByUser} />
        }
        <div className="row">
          <div className="col-md-8">
            <h3>{this.state.mode === "listens" ? "Recent listens" : "Playlist"}</h3>

            {!this.state.listens.length ?
              <p className="lead" className="text-center">No listens :/</p> :
              <div>
                <table className="table table-condensed table-striped listens-table" id="listens">
                  <thead>
                    <tr>
                      <th>Track</th>
                      <th>Artist</th>
                      <th>Time</th>
                      {this.state.mode === "follow" && <th>User</th>}
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {this.state.listens
                      .sort((a, b) => a.playing_now ? -1 : b.playing_now ? 1 : 0)
                      .map((listen, index) => {
                        return (
                          <tr key={index} className={`listen ${this.isCurrentListen(listen) ? 'info' : ''} ${listen.playing_now ? 'playing_now' : ''}`}  >
                            <td>{getTrackLink(listen)}</td>
                            <td>{getArtistLink(listen)}</td>
                            {listen.playing_now ?
                              <td><span className="fab fa-spotify" aria-hidden="true"></span> Playing now</td>
                              :
                              <td>
                                <abbr className="timeago" title={listen.listened_at_iso}>
                                  {listen.listened_at_iso ? $.timeago(listen.listened_at_iso) : $.timeago(listen.listened_at * 1000)}
                                </abbr>
                              </td>
                            }
                            {this.state.mode === "follow" && <td>{listen.user_name}</td>}
                            <td className="playButton">{getPlayButton(listen, this.playListen.bind(this, listen))}</td>
                          </tr>
                        )
                      })
                    }

                  </tbody>
                </table>

                {this.state.mode === "listens" &&
                  <ul className="pager">
                    <li className="previous" className={!this.props.previous_listen_ts ? 'hidden' : ''}>
                      <a href={`${this.props.profile_url}?min_ts=${this.props.previous_listen_ts}`}>&larr; Previous</a>
                    </li>
                    <li className="next" disabled={!this.props.next_listen_ts ? 'hidden' : ''}>
                      <a href={`${this.props.profile_url}?max_ts=${this.props.next_listen_ts}`}>Next &rarr;</a>
                    </li>
                  </ul>
                }
              </div>


            }
          </div>
          <div className="col-md-4" style={{ position: "-webkit-sticky", position: "sticky", top: 20 }}>
            {this.props.spotify_access_token ?
              <SpotifyPlayer
                ref={this.spotifyPlayer}
                listens={spotifyListens}
                direction={this.state.mode === "follow" ? "up" : "down"}
                spotify_access_token={this.props.spotify_access_token}
                onCurrentListenChange={this.handleCurrentListenChange}
                currentListen={this.state.currentListen}
              /> :
              // Fallback embedded player
              <div className="col-md-4 text-right">
                <iframe src={getSpotifyEmbedSrc()}
                  width="300" height="380" frameBorder="0" allowtransparency="true" allow="encrypted-media">
                </iframe>
              </div>
            }
          </div>
        </div>
      </div>);
  }
}

class FollowUsers extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      users: props.initialList || []
    }
    this.addUserToList = this.addUserToList.bind(this);
    this.reorderUser = this.reorderUser.bind(this);
  }

  addUserToList(event) {
    event.preventDefault();
    if (this.textInput.value === "" ||
      this.state.users.find(user => user === this.textInput.value))
    {
      return;
    }
    this.setState(prevState => {
      return { users: prevState.users.concat([this.textInput.value]) }
    }, () => {
      this.textInput.value = "";
      this.props.onUserListChange(this.state.users);
    });
  }
  removeUserFromList(index) {
    this.setState(prevState => {
      prevState.users.splice(index, 1);
      return { users: prevState.users }
    }, () => { this.props.onUserListChange(this.state.users) });
  }

  reorderUser(currentIndex, targetIndex) {
    this.setState(prevState => {
      var element = prevState.users[currentIndex];
      prevState.users.splice(currentIndex, 1);
      prevState.users.splice(targetIndex, 0, element);
      return { users: prevState.users }
    });
  }

  render() {
    const noTopBottomPadding = {
      paddingTop: 0,
      paddingBottom: 0
    };
    return (
      <div className="panel panel-primary">
        <div className="panel-heading">
          <i class="fas fa-sitemap fa-2x fa-flip-vertical"></i>
          <span style={{ fontSize: "x-large", marginLeft: "0.55em", verticalAign: "middle" }}>
            Follow users
              </span>
        </div>
        <div className="panel-body">
          <div className="text-muted">
            Add a user to discover what they are listening to:
              </div>
          <hr />
          <div className="input-group">
            <input type="text" className="form-control" placeholder="Username…"
              ref={(input) => this.textInput = input}
            />
            <span className="input-group-btn btn-primary">
              <button className="btn btn-primary" type="button" onClick={this.addUserToList}>
                <span className="fa fa-plus-circle" aria-hidden="true"></span> Add
              </button>
            </span>
          </div>
          <table className="table table-condensed table-striped listens-table">
            <thead>
              <tr>
                <th colSpan="2" width="50px">Order</th>
                <th>User</th>
                <th width="50%">Listening now</th>
                <th width="25px"></th>
                <th width="85px"></th>
              </tr>
            </thead>
            <tbody>
              {this.state.users.map((user, index) => {
                return (
                  <tr key={user} className={this.props.playingNow[user] && "playing_now"}>
                    <td>
                      {index + 1}
                    </td>
                    <td>
                      <span className="btn-group btn-group-xs" role="group" aria-label="Reorder">
                        {index > 0 &&
                          <button className="btn btn-info"
                            onClick={this.reorderUser.bind(this, index, index - 1)}>
                            <span className="fa fa-chevron-up"></span>
                          </button>
                        }
                        {index < this.state.users.length - 1 &&
                          <button className="btn btn-info"
                            onClick={this.reorderUser.bind(this, index, index + 1)}>
                            <span className="fa fa-chevron-down"></span>
                          </button>
                        }
                      </span>
                    </td>
                    <td>
                      {user}
                    </td>
                    <td>
                      {this.props.playingNow[user] &&
                        <React.Fragment>
                          {getTrackLink(this.props.playingNow[user])}
                          <span className="small"> — {getArtistLink(this.props.playingNow[user])}</span>
                        </React.Fragment>
                      }
                    </td>
                    <td style={noTopBottomPadding}>
                      <button className="btn btn-danger" type="button" aria-label="Remove"
                        onClick={this.removeUserFromList.bind(this, index)}>
                        <span className="fa fa-trash-alt"></span>
                      </button>
                    </td>
                    <td className="playButton">
                      {this.props.playingNow[user] &&
                        getPlayButton(this.props.playingNow[user], this.props.playListen.bind(this, this.props.playingNow[user]))
                      }
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

}


let domContainer = document.querySelector('#react-listens');
let propsElement = document.getElementById('react-props');
let reactProps;
try
{
  reactProps = JSON.parse(propsElement.innerHTML);
  // console.log("props",reactProps);
}
catch (err)
{
  console.error("Error parsing props:", err);
}
ReactDOM.render(<RecentListens {...reactProps} />, domContainer);

window.onSpotifyWebPlaybackSDKReady = window.onSpotifyWebPlaybackSDKReady || console.log;


