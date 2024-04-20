import spotipy
import requests
from troi import Recording
import troi.playlist
from troi.musicbrainz.recording import RecordingListElement
import sys

def import_from_spotify(token, user, playlist_id):
    tracks_from_playlist, title, description = get_tracks_from_playlist(token, playlist_id)
    tracks = []
    for track in tracks_from_playlist["items"]:
        artists = track['track'].get('artists', [])
        artist_names = []
        for a in artists:
            name = a.get('name')
            if name is not None:
                artist_names.append(name)
        artist_name = ', '.join(artist_names)
        tracks.append({
            "track_name": track['track']['name'],
            "artist_name": artist_name,
        })
    # select track_name and artist_name for each track
    mbid_mapped_tracks = [mbid_mapping_spotify(track["track_name"], track["artist_name"]) for track in tracks]
    # pass the tracks as Recording
    recordings=[]
    if mbid_mapped_tracks:
        for track in mbid_mapped_tracks:
            if track is not None and "recording_mbid" in track:
                recordings.append(Recording(mbid=track["recording_mbid"]))
    else:
        return None
    
    recording_list = RecordingListElement(recordings)
    try:
        playlist = troi.playlist.PlaylistElement()
        playlist.set_sources(recording_list)
        result = playlist.generate()
        
        playlist.playlists[0].name = title
        playlist.playlists[0].descripton = description
        
        print("done.")
    except troi.PipelineError as err:
        print("Failed to generate playlist: %s" % err, file=sys.stderr)
        return None  
    
    if result is not None and user:
        for url, _ in playlist.submit(user, None):
            print("Submitted playlist: %s" % url)

    result = playlist.get_jspf()
    result.update({'identifier': url})
    
    return result

def get_tracks_from_playlist(spotify_token, playlist_id):
    """ Get the tracks from Spotify playlist.
    """
    sp = spotipy.Spotify(auth=spotify_token, requests_timeout=10, retries=10)
    playlist_info = sp.playlist(playlist_id)
    playlists = sp.playlist_items(playlist_id, limit=100)
    name = playlist_info["name"]
    description = playlist_info["description"]
    
    return playlists, name, description

def mbid_mapping_spotify(track_name, artist_name):
    url = "https://api.listenbrainz.org/1/metadata/lookup/"
    params = {
        "artist_name": artist_name,
        "recording_name": track_name,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print("Error occurred:", response.status_code)