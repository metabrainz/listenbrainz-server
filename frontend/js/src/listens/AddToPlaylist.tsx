import * as React from "react";
import GlobalAppContext from "../utils/GlobalAppContext";
import { has } from "lodash";
import { PLAYLIST_URI_PREFIX,  listenToJSPFTrack } from "../playlists/utils";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlusCircle } from "@fortawesome/free-solid-svg-icons";
import { toast } from "react-toastify";
import { ToastMsg } from "../notifications/Notifications";

type AddToPlaylistProps = {
	listen: Listen | JSPFTrack;
}

export default function  AddToPlaylist(props:AddToPlaylistProps) {
	const { listen } = props;
	const { APIService, currentUser } = React.useContext(GlobalAppContext);
	const [playlists, setPlaylists] = React.useState<Array<JSPFObject>>([]);
	// fetch user's playlists
	// store list of playlists in local storage
	// add a virtualized dropdown with the list of playlists

	const addToPlaylist = React.useCallback(async (event:React.MouseEvent<HTMLButtonElement>)=>{
		if(!currentUser?.auth_token){
			throw new Error("You are not logged in");
		}
		try {
			const { currentTarget } = event;
			const { name:playlistName, dataset } = currentTarget;
			// const { playlist } = dataset;
			const playlistIdentifier = currentTarget.getAttribute("data-playlist-identifier");
			let trackToSend;
			if(has(listen,"title")){
				trackToSend = listen as JSPFTrack;
			} else {
				trackToSend = listenToJSPFTrack(listen as Listen);
			}
			if( !playlistIdentifier){
				throw new Error(`No identifier for playlist ${playlistName}`);
			}
			const playlistId = playlistIdentifier?.replace(PLAYLIST_URI_PREFIX, "");
			const status =  await APIService.addPlaylistItems(currentUser.auth_token,playlistId,[trackToSend]);
			if (status === 200){
				toast.success(<ToastMsg title="Added track" message={
					<>
						Successfully added <i>{trackToSend.title}</i> to playlist <a
						href={playlistIdentifier}>
							{playlistName}
						</a>
					</>
				} />, {
					toastId: "success-add-track-to-playlist",
				  });
			} else {
				throw new Error("Could not add track to playlist");
			}
		} catch (error) {
			toast.error(<ToastMsg title="Error adding track to playlist" message={
				<>
					Could not add track to playlist:<br/>
					{error.toString()}
				</>
			} />, {
				toastId: "error-add-track-to-playlist",
			  });
		}
	},[listen,currentUser.auth_token]);
	return (<>
		<button
		className="dropdown-toggle"
		title="Add to playlist"
		type="button"
		data-toggle="dropdown"
		aria-label="Add to playlist"
		role="menuitem"
		>
		<FontAwesomeIcon icon={faPlusCircle} /> Add to playlist… <div className="caret" />
		</button>
		<ul className="dropdown-menu" role="menu">
			{playlists?.map(jspfObject=>{
				const {playlist} = jspfObject;
				return (
				<li>
					<button type="button" name={playlist.title} data-playlist-identifier={playlist.identifier} onClick={addToPlaylist}>
						{playlist.title}
					</button>
				</li>)
			})}
		</ul>
	</>
	)
}