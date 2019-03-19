'use strict';

import * as timeago from 'time-ago';

import { faListUl, faMusic } from '@fortawesome/free-solid-svg-icons'
import {getArtistLink, getPlayButton, getSpotifyEmbedUriFromListen, getTrackLink} from './utils.jsx';

import APIService from './api-service';
import { AlertList } from 'react-bs-notifier';
import {FollowUsers} from './follow-users.jsx';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import React from 'react';
import ReactDOM from 'react-dom';
import {SpotifyPlayer} from './spotify-player.jsx';
import {isEqual as _isEqual} from 'lodash';
import io from 'socket.io-client';

class RecentListens extends React.Component {

  spotifyListens = [];
  constructor(props) {
    super(props);
    this.state = {
      alerts: [],
      listens: props.listens || [],
      currentListen : null,
      mode: props.mode,
      followList: props.follow_list || [],
      playingNowByUser: {},
      saveUrl: props.save_url || '',
      listName: props.follow_list_name,
      listId: props.follow_list_id,
      direction: "down"
    };
    this.connectWebsockets = this.connectWebsockets.bind(this);
    this.getRecentListensForFollowList = this.getRecentListensForFollowList.bind(this);
    this.handleCurrentListenChange = this.handleCurrentListenChange.bind(this);
    this.handleFollowUserListChange = this.handleFollowUserListChange.bind(this);
    this.handleSpotifyAccountError = this.handleSpotifyAccountError.bind(this);
    this.handleSpotifyPermissionError = this.handleSpotifyPermissionError.bind(this);
    this.isCurrentListen = this.isCurrentListen.bind(this);
    this.newAlert = this.newAlert.bind(this);
    this.onAlertDismissed = this.onAlertDismissed.bind(this);
    this.playListen = this.playListen.bind(this);
    this.receiveNewListen = this.receiveNewListen.bind(this);
    this.receiveNewPlayingNow = this.receiveNewPlayingNow.bind(this);
    this.spotifyPlayer = React.createRef();

    this.APIService = new APIService(props.api_url || `${window.location.origin}/1`);
  }

  componentDidMount(){
    if(this.state.mode === "listens" || this.state.mode === "follow"){
      this.connectWebsockets();
    }
    if(this.state.mode === "follow" && !this.state.listens.length){
      this.getRecentListensForFollowList();
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

  handleFollowUserListChange(userList, dontSendUpdate){
    if(!Array.isArray(userList)){
      console.error("Expected array in handleFollowUserListChange, got", typeof userList);
      return;
    }
    let previousFollowList;
    this.setState(prevState => {
      previousFollowList = prevState.followList;
      return {
        followList: userList
      }
    }, ()=>{
      if(dontSendUpdate){
        return;
      }
      if(!this._socket){
        this.connectWebsockets();
        return;
      }
      console.debug("Emitting user list to websockets:", userList);
      this._socket.emit("json", {user: this.props.user.name, 'follow': userList});
      if(this.state.mode === "follow" && _.difference(userList, previousFollowList)){
        this.getRecentListensForFollowList();
      }
    })
  }

  handleSpotifyAccountError(error){
    this.newAlert("danger","Spotify account error", error);
    this.setState({canPlayMusic: false})
  }

  handleSpotifyPermissionError(error) {
    console.error(error);
    this.setState({canPlayMusic: false});
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
      const listens = prevState.listens;
      // Crop listens array to 100 max
      if(listens.length >= 100) {
        if (prevState.mode === "follow"){
          listens.shift();
        } else {
          listens.pop()
        }
      }

      if (prevState.mode === "follow"){
        listens.push(newListen);
      } else {
        listens.unshift(newListen);
      }
      return { listens }
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

  getRecentListensForFollowList(){
    if(!this.state.followList.length){
      return
    }
    this.APIService.getRecentListensForUsers(this.state.followList)
      .then(listens => this.setState({ listens:  _.orderBy(listens, "listened_at", "asc")}))
      .catch(error => this.newAlert('danger', 'Could not get recent listens', error));
  }

  newAlert(type, headline, message) {
    const newAlert ={
      id: (new Date()).getTime(),
      type,
      headline,
      message
    };

    this.setState({
      alerts: [...this.state.alerts, newAlert]
    });
  }
  onAlertDismissed(alert) {
    const alerts = this.state.alerts;

    // find the index of the alert that was dismissed
    const idx = alerts.indexOf(alert);

    if (idx >= 0) {
      this.setState({
        // remove the alert from the array
        alerts: [...alerts.slice(0, idx), ...alerts.slice(idx + 1)]
      });
    }
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
        <AlertList
          position="bottom-right"
          alerts={this.state.alerts}
          timeout={15000}
          dismissTitle="Dismiss"
          onDismiss={this.onAlertDismissed}
        />
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
        <div className="row">
          <div className="col-md-8">

            <h3>{(this.state.mode === "listens" || this.state.mode === "recent" )? "Recent listens" : "Playlist"}</h3>

            {!this.state.listens.length &&
              <div className="lead text-center">
                <p>No listens yet</p>
                {this.state.mode === "follow" &&
                  <div title="Load recent listens" className="btn btn-primary" onClick={this.getRecentListensForFollowList}>
                    <FontAwesomeIcon icon={faListUl}/>&nbsp;&nbsp;Load recent listens
                  </div>
                }
              </div>
            }
            {this.state.listens.length > 0 &&
              <div>
                <table className="table table-condensed table-striped listens-table" id="listens">
                  <thead>
                    <tr>
                      <th>Track</th>
                      <th>Artist</th>
                      <th>Time</th>
                      {(this.state.mode === "follow" || this.state.mode === "recent") &&
                        <th>User</th>
                      }
                      <th width="50px"></th>
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
                              <td><FontAwesomeIcon icon={faMusic}/> Playing now</td>
                              :
                              <td>
                                <abbr title={listen.listened_at_iso}>
                                    {listen.listened_at_iso ? timeago.ago(listen.listened_at_iso) : timeago.ago(listen.listened_at * 1000)}
                                </abbr>
                              </td>
                            }
                            {(this.state.mode === "follow" || this.state.mode === "recent") &&
                              <td><a href={`/user/${listen.user_name}`} target="_blank">{listen.user_name}</a></td>
                            }
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
            <br/>
            {this.state.mode === "follow" &&
              <FollowUsers onUserListChange={this.handleFollowUserListChange}
                followList={this.state.followList} playListen={this.playListen.bind(this)}
                playingNow={this.state.playingNowByUser} saveUrl={this.state.saveUrl}
                listName={this.state.listName} listId={this.state.listId} creator={this.props.user}
                newAlert={this.newAlert}/>
            }
          </div>
          <div className="col-md-4" style={{ position: "-webkit-sticky", position: "sticky", top: 20 }}>
            {this.props.spotify.access_token && this.state.canPlayMusic !== false ?
              <SpotifyPlayer
                APIService={this.APIService}
                ref={this.spotifyPlayer}
                listens={spotifyListens}
                direction={this.state.direction}
                spotify_user={this.props.spotify}
                onCurrentListenChange={this.handleCurrentListenChange}
                onAccountError={this.handleSpotifyAccountError}
                onPermissionError={this.handleSpotifyPermissionError}
                currentListen={this.state.currentListen}
                newAlert={this.newAlert}
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


let domContainer = document.querySelector('#react-container');
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


