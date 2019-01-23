'use strict';

class RecentListens extends React.Component {
	constructor(props) {
		super(props);
		this.state = { listens: props.listens };
		this.playSpotifyId.bind(this);
	}
	
	playSpotifyId(spotifyId){
		console.log("asked to play spotifyId",spotifyId);
	}
	
	render() {

		const getArtistLink = listen => {
			if(listen.track_metadata.additional_info.artist_mbids && listen.track_metadata.additional_info.artist_mbids.length){
				return (<a href={`http://musicbrainz.org/artist/${listen.track_metadata.additional_info.artist_mbids[0]}`}>
					{listen.track_metadata.artist_name}
					</a>);
			}
			return listen.track_metadata.artist_name
		}
		
		const getTrackLink = listen => {
			if(listen.track_metadata.additional_info.recording_mbid) {
			return (<a href={`http://musicbrainz.org/recording/${listen.track_metadata.additional_info.recording_mbid}`}>
				{ listen.track_metadata.track_name }
				</a>);
			}
			return listen.track_metadata.track_name;
		}


		return (
			<div>
				<h3> Statistics </h3>

				<div className="row">
					<div className="col-md-8">
					<table className="table table-border table-condensed table-striped">
							<tbody>
								{props.listen_count && 
								<tr>
									<td>Listen count</td>
									<td>{ props.listen_count }</td>
								</tr>
								}
								{ props.artist_count &&
								<tr>
									<td>Artist count</td>
									<td>{ props.artist_count }</td>
								</tr>
								}
							</tbody>
						</table>
					</div>
				</div>
			<h3>Recent listens</h3>
			
			{ !this.state.listens.length ?
				<p className="lead" style="text-align: center;">No listens :/</p> :
				
				<div className="row">
				<div className="col-md-8">
				<table className="table table-condensed table-striped">
				<thead>
				<tr>
				<th>artist</th>
				<th>track</th>
				<th>time</th>
				</tr>
				</thead>
				<tbody>
				{this.state.listens.map((listen,index) => {
					if (listen.playing_now) {
						return (
							<tr id="playing_now" key={index}>
							<td>{ listen.track_metadata.artist_name }</td>
							<td>{ listen.track_metadata.track_name }</td>
							<td><span className="glyphicon glyphicon-play" aria-hidden="true"></span> Playing now</td>
							</tr>
							)
						} else {
							return (
								<tr key={index}>
								<td>
									{getArtistLink(listen)}
								</td>
								<td>
									{listen.track_metadata.additional_info.spotify_id &&
										<button className="btn btn-default btn-sm" onClick={this.playSpotifyId(listen.track_metadata.additional_info.spotify_id)}>
										<span className="fab fa-spotify"></span> Play
										</button>
									} {getTrackLink(listen)}
								</td>
								<td><abbr className="timeago" title={listen.listened_at_iso}>{ $.timeago(listen.listened_at_iso) }</abbr></td>
								</tr>
								)
							}
						})
					}
					
					</tbody>
					</table>
					
					<ul className="pager">
						<li className="previous" disabled={!props.previous_listen_ts}>
							<a href={`${props.profile_url}?min_ts=${props.previous_listen_ts}`}>&larr; Previous</a>
						 </li>
						<li className="next" disabled={!props.next_listen_ts}>
							<a href={`${props.profile_url}?max_ts=${props.next_listen_ts}`}>Next &rarr;</a>
						</li>
					</ul>
				</div>
				</div>
				
			}
			</div>
			);
		}
	}

	let domContainer = document.querySelector('#react-listens');
	let propsElement = document.getElementById('react-props');
	let props;
	try{
		 props = JSON.parse(propsElement.innerHTML);
		 console.log("props",props);
	}
	catch(err){
		console.error("Error parsing props:", err);
	}
	ReactDOM.render(<RecentListens {...props}/>, domContainer);