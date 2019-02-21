'use strict';

import '../lib/spotify-player-sdk-1.6.0';

import * as _isEqual from 'lodash.isequal';
import * as timeago from 'time-ago';

import {getArtistLink, getPlayButton, getSpotifyEmbedUriFromListen, getTrackLink} from './utils.jsx';

import {FollowUsers} from './follow-users.jsx';
import React from 'react';
import ReactDOM from 'react-dom';
import {SpotifyPlayer} from './spotify-player.jsx';
import io from 'socket.io-client';

class RecentListens extends React.Component {

  spotifyListens = [];
  constructor(props) {
    super(props);
    this.state = {
      listens: props.listens || [],
      currentListen : null,
      mode: props.mode,
      followList: props.follow_list || [],
      playingNowByUser: {}
    };
    this.isCurrentListen = this.isCurrentListen.bind(this);
    this.handleCurrentListenChange = this.handleCurrentListenChange.bind(this);
    this.playListen = this.playListen.bind(this);
    this.spotifyPlayer = React.createRef();
    this.receiveNewListen = this.receiveNewListen.bind(this);
    this.receiveNewPlayingNow = this.receiveNewPlayingNow.bind(this);
    this.handleFollowUserListChange = this.handleFollowUserListChange.bind(this);
    this.connectWebsockets = this.connectWebsockets.bind(this);
  }

  componentDidMount(){
    if(this.state.mode === "listens" || this.state.mode === "follow"){
      this.connectWebsockets();
    }
  }

  connectWebsockets(){
    this._socket = io.connect(this.props.web_sockets_server_url);
    this._socket.on('connect', () => {
      console.debug("Connected to websocket!");
      switch (this.state.mode) {
        case "follow":
          this.handleFollowUserListChange(this.state.followList);
          break;
        case "listens":
        default:
          this.handleFollowUserListChange([this.props.user.name]);
          break;
      }
    });
    this._socket.on('listen', (data) => {
      console.debug('New listen!');
      this.receiveNewListen(data);
    });
    this._socket.on('playing_now', (data) => {
      console.debug('New now playing notification!')
      this.receiveNewPlayingNow(data);
    });
  }

  handleFollowUserListChange(userList){
    if(!Array.isArray(userList)){
      console.error("Expected array in handleFollowUserListChange, got", typeof userList);
      return;
    }
    this.setState({followList: userList}, ()=>{
      if(!this._socket){
        this.connectWebsockets();
        return;
      }
      console.debug("Emitting user list to websockets:", userList);
      this._socket.emit("json", {user: this.props.user.name, 'follow': userList});
    })
  }

  playListen(listen){
    if(this.spotifyPlayer.current){
      this.spotifyPlayer.current.playListen(listen);
      return;
    } else {
      // For fallback embedded player
      this.setState({currentListen:listen});
      return;
    }
  }

  receiveNewListen(newListen){
    try {
      newListen = JSON.parse(newListen);
    } catch (error) {
      console.error(error);
    }
    console.debug(typeof newListen, newListen);
    this.setState(prevState =>{
      return { listens: [newListen].concat(prevState.listens)}
    })
  }
  receiveNewPlayingNow(newPlayingNow){
    try {
      newPlayingNow = JSON.parse(newPlayingNow);
    } catch (error) {
      console.error(error);
    }
    newPlayingNow.playing_now = true;

    this.setState(prevState =>{
      if(prevState.mode === "follow"){
        const userName = newPlayingNow.user_name;
        return {playingNowByUser: Object.assign(
          {},
          prevState.playingNowByUser,
          {[userName]:newPlayingNow}
          )
        }
      }
      const indexOfPreviousPlayingNow = prevState.listens.findIndex(listen => listen.playing_now);
      prevState.listens.splice(indexOfPreviousPlayingNow, 1);
      return { listens: [newPlayingNow].concat(prevState.listens)}
    })
  }

  handleCurrentListenChange(listen){
    this.setState({currentListen:listen});
  }
  isCurrentListen(listen){
    return this.state.currentListen && _isEqual(listen,this.state.currentListen);
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
            followList={this.state.followList} playListen={this.playListen.bind(this)}
            playingNow={this.state.playingNowByUser} />
        }
        <div className="row">
          <div className="col-md-8">
            <h3>{(this.state.mode === "listens" || this.state.mode === "recent" )? "Recent listens" : "Playlist"}</h3>

            {!this.state.listens.length ?
              <p className="lead" className="text-center">No listens :/</p> :
              <div>
                <table className="table table-condensed table-striped listens-table" id="listens">
                  <thead>
                    <tr>
                      <th>Track</th>
                      <th>Artist</th>
                      <th>Time</th>
                      {(this.state.mode === "follow" || this.state.mode === "recent") && <th>User</th>}
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {this.state.listens
                      .sort((a, b) => a.playing_now ? -1 : b.playing_now ? 1 : 0)
                      .map((listen, index) => {
                        return (
                          <tr key={index}
                            onDoubleClick={this.playListen.bind(this, listen)}
                            className={`listen ${this.isCurrentListen(listen) ? 'info' : ''} ${listen.playing_now ? 'playing_now' : ''}`}  >
                            <td>{getTrackLink(listen)}</td>
                            <td>{getArtistLink(listen)}</td>
                            {listen.playing_now ?
                              <td><span className="fab fa-spotify" aria-hidden="true"></span> Playing now</td>
                              :
                              <td>
                                <abbr title={listen.listened_at_iso}>
                                    {listen.listened_at_iso ? timeago.ago(listen.listened_at_iso) : timeago.ago(listen.listened_at * 1000)}
                                </abbr>
                              </td>
                            }
                            {(this.state.mode === "follow" || this.state.mode === "recent") && <td><a href={`/user/${listen.user_name}`}>{listen.user_name}</a></td>}
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
ReactDOM.render(<RecentListens {...reactProps}/>, domContainer);


