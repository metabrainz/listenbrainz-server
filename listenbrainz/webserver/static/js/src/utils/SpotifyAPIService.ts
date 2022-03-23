// Maybe we don't need to reinvent the wheel, and we can use this library instead?
// https://github.com/jmperez/spotify-web-api-js

/* eslint-disable camelcase */

import { searchForSpotifyTrack } from "./utils";

export default class SpotifyAPIService {
  static async checkStatus(response: Response) {
    if (response.status >= 200 && response.status < 300) {
      return;
    }
    const error: SpotifyAPIError = await response.json();
    throw error;
  }

  static checkToken(userToken?: string) {
    if (!userToken) {
      throw new Error("You must be logged in with Spotify");
    }
  }

  APIBaseURI: string = "https://api.spotify.com/v1";
  private spotifyUser?: SpotifyUser;
  private spotifyUserId?: string;

  constructor(spotifyUser?: SpotifyUser) {
    if (spotifyUser) {
      this.spotifyUser = spotifyUser;
    } else {
      throw new Error(
        "Valid Spotify user must be passed to initialize SpotifyAPIService"
      );
    }
  }

  getAlbumArtFromSpotifyTrackID = async (
    spotifyTrackID: string
  ): Promise<string | undefined> => {
    if (!spotifyTrackID) {
      return undefined;
    }
    try {
      const response = await fetch(
        `${this.APIBaseURI}/tracks/${spotifyTrackID}`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${this.spotifyUser?.access_token}`,
          },
        }
      );
      if (response.ok) {
        const track: SpotifyTrack = await response.json();
        return track.album?.images?.[0]?.url;
      }
    } catch (error) {
      return undefined;
    }
    return undefined;
  };

  setUserToken = (userToken: string) => {
    if (!userToken) {
      throw new Error("No Spotify user token to set");
    }
    if (!this.spotifyUser) {
      throw new Error(
        "Spotify API was instantiated without a user, cannot set token"
      );
    }
    this.spotifyUser.access_token = userToken;
  };

  getSpotifyUserId = async () => {
    if (this.spotifyUserId) {
      return this.spotifyUserId;
    }
    const response = await fetch(`${this.APIBaseURI}/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${this.spotifyUser?.access_token}`,
      },
    });
    await SpotifyAPIService.checkStatus(response);
    const user: SpotifyUserObject = await response.json();
    this.spotifyUserId = user.id;
    return user.id;
  };

  // Must grant the playlist-modify-public and/or playlist-modify-private scopes
  createPlaylist = async (
    title: string,
    isPublic?: boolean,
    description?: string,
    collaborative: boolean = false
  ): Promise<SpotifyPlaylistObject> => {
    SpotifyAPIService.checkToken(this.spotifyUser?.access_token);

    if (!title) {
      throw new SyntaxError("playlist title missing");
    }
    const userId = await this.getSpotifyUserId();
    const url = `${this.APIBaseURI}/users/${userId}/playlists`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Must grant the playlist-modify-public and/or playlist-modify-private scopes
        Authorization: `Bearer ${this.spotifyUser?.access_token}`,
      },
      body: JSON.stringify({
        name: title,
        description,
        public: isPublic,
        collaborative,
      }),
    });
    await SpotifyAPIService.checkStatus(response);
    const result: SpotifyPlaylistObject = await response.json();

    return result;
  };

  getPlaylist = async (playlistId: string): Promise<SpotifyPlaylistObject> => {
    SpotifyAPIService.checkToken(this.spotifyUser?.access_token);

    if (!playlistId) {
      throw new SyntaxError("Spotify playlist ID missing");
    }
    const url = `${this.APIBaseURI}/playlists/${playlistId}`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${this.spotifyUser?.access_token}`,
      },
    });
    await SpotifyAPIService.checkStatus(response);
    const result: SpotifyPlaylistObject = await response.json();

    return result;
  };

  // Requires the playlist-read-private and playlist-read-collaborative scopes
  // to return priavate and collaborative playlists
  getAllPlaylists = async (): Promise<SpotifyPlaylistObject[]> => {
    SpotifyAPIService.checkToken(this.spotifyUser?.access_token);

    const url = `${this.APIBaseURI}/me/playlists`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${this.spotifyUser?.access_token}`,
      },
    });
    await SpotifyAPIService.checkStatus(response);
    const result: SpotifyPagingObject<SpotifyPlaylistObject> = await response.json();

    return result.items;
  };

  addSpotifyTracksToPlaylist = async (
    playlistId: string,
    spotifyURIs: string[] // Spotify URIs
  ): Promise<string> => {
    SpotifyAPIService.checkToken(this.spotifyUser?.access_token);

    if (!playlistId) {
      throw new SyntaxError("Spotify playlist ID missing");
    }
    const url = `${this.APIBaseURI}/playlists/${playlistId}/tracks`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Must grant the playlist-modify-public and/or playlist-modify-private scopes
        Authorization: `Bearer ${this.spotifyUser?.access_token}`,
      },
      body: JSON.stringify({
        uris: spotifyURIs,
      }),
    });
    await SpotifyAPIService.checkStatus(response);
    const spotifySnapshotId: string = await response.json();

    return spotifySnapshotId;
  };

  /* eslint-disable no-await-in-loop */
  searchForSpotifyURIs = async (tracks: JSPFTrack[]): Promise<string[]> => {
    const tracksCopy = [...tracks];
    const uris: string[] = [];
    while (tracksCopy.length > 0) {
      const track = tracksCopy[0];
      try {
        const spotifyTrack = await searchForSpotifyTrack(
          this.spotifyUser?.access_token,
          track.title,
          track.creator,
          track.album
        );
        if (spotifyTrack?.uri) {
          uris.push(spotifyTrack.uri);
        }
        tracksCopy.shift();
      } catch (error) {
        if (error.status === 429) {
          // Too many requests, take a nap before continuing
          await new Promise((resolve) => setTimeout(resolve, 600));
        } else {
          throw error;
        }
      }
    }
    return uris;
  };
  /* eslint-enable no-await-in-loop */
}
