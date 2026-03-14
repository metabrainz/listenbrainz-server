# Spotify Permissions Issue: Explained in Layman's Terms

## The Problem
In ListenBrainz, we ask users for permission to access their Spotify accounts. Spotify groups these permissions into "scopes" (think of them like keys to specific rooms in a house). ListenBrainz asks for these permissions in two main categories:

1. **Listen Permissions (`SPOTIFY_LISTEN_PERMISSIONS`)**: Permissions needed to see what music you are currently listening to, so we can record your "listens" (play history).
2. **Playlist Permissions (`SPOTIFY_PLAYLIST_PERMISSIONS`)**: Permissions needed to read or manage your Spotify playlists, so we can import them or export your ListenBrainz recommendations back to Spotify.

**The Mistake:**
When the ability to read private and collaborative playlists was added to the code, the specific permissions needed for this (`playlist-read-private` and `playlist-read-collaborative`) were accidentally put into the **Listen Permissions** group instead of the **Playlist Permissions** group. 

This caused two problems:
- If a user just wanted to connect Spotify to track their listening history, Spotify would suddenly ask them for permission to read their private and shared playlists too, which is confusing and asks for more access than necessary.
- The playlist management code wasn't looking in the right place for its permissions.

## The Fix (Step by Step)

1. **Moving the Permissions to the Right Group** 
   In `listenbrainz/domain/spotify.py`, we moved `'playlist-read-private'` and `'playlist-read-collaborative'` out of `SPOTIFY_LISTEN_PERMISSIONS` and correctly placed them into `SPOTIFY_PLAYLIST_PERMISSIONS`. 
   *Result: ListenBrainz now only asks to read playlists when the user actually wants to use playlist features!*

2. **Updating the Warning Signs (Error Messages)** 
   In the code that handles playlist requests (`listenbrainz/webserver/views/playlist_api.py`), if a user tries to import/export a playlist without granting the right permissions, the server returns an error. We updated 4 of these error messages to explicitly tell the user they are missing these newly required scopes.

3. **Updating the Automated Tests** 
   In our automated testing suite (`listenbrainz/tests/integration/test_playlist_api.py`), we had to update the "expectations" of our tests. We updated the tests to verify that the server returns our new, updated error message text. We also added the new permissions to the "happy path" tests (tests that simulate a completely successful playlist operation with all correct permissions).

### Summary
We simply organized the requested permissions into their correct categories and updated the related error messages and tests to reflect that change.
