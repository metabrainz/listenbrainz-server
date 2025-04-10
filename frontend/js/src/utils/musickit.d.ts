interface Window {
  MusicKit: typeof MusicKit.MusicKitInstance;
}

declare namespace MusicKit {
  /**
   * Configure a MusicKit instance.
   */
  async function configure(
    configuration: Configuration
  ): Promise<MusicKitInstance>;
  /**
   * Returns the configured MusicKit instance.
   */
  function getInstance(): MusicKitInstance;

  interface Song {
    attributes: {
      albumName: string;
      artistName: string;
      artwork: {
        bgColor: string;
        height: number;
        textColor1: string;
        textColor2: string;
        textColor3: string;
        textColor4: string;
        url: string;
        width: number;
      };
      composerName: string;
      discNumber: number;
      durationInMillis: number;
      genreNames: string[];
      hasCredits: boolean;
      hasLyrics: boolean;
      isAppleDigitalMaster: boolean;
      isrc: string;
      name: string;
      playParams: {
        id: string;
        kind: string;
      };
      previews: [
        {
          url: string;
        }
      ];
      releaseDate: string;
      trackNumber: number;
      url: string;
    };
    href: string;
    id: string;
    type: string;
  }

  interface APISearchResult {
    meta: {};
    results: {
      songs: {
        data: Song[];
        href: string;
        next: string;
      };
    };
  }

  /**
   * This class represents the Apple Music API.
   */
  interface API {
    /**
     * Search the catalog using a query.
     *
     * @param path The path to the Apple Music API endpoint, without a hostname, and including a leading slash /
     * @param parameters A query parameters object that is serialized and passed
     * @param options An object with additional options to control how requests are made
     * directly to the Apple Music API.
     */
    music(
      path: string,
      parameters?: any,
      options?: any
    ): Promise<{ data: APISearchResult }>;
  }

  /**
   * An object that represents artwork.
   */
  interface Artwork {
    bgColor: string;
    height: number;
    width: number;
    textColor1: string;
    textColor2: string;
    textColor3: string;
    textColor4: string;
    url: string;
  }

  /**
   * The playback states of the music player.
   */
  enum PlaybackStates {
    none,
    loading,
    playing,
    paused,
    stopped,
    ended,
    seeking,
    waiting,
    stalled,
    completed,
  }

  /**
   * This class represents a single media item.
   */
  interface MediaItem {
    albumInfo: string;
    albumName: string;
    artistName: string;
    artwork: Artwork;
    artworkURL: string;
    attributes: any;
    contentRating: string;
    discNumber: number;
    id: string;
    info: string;
    isExplicitItem: boolean;
    isPlayable: boolean;
    isPreparedToPlay: boolean;
    isrc: string;
    playbackDuration: number;
    playlistArtworkURL: string;
    playlistName: string;
    previewURL: string;
    releaseDate?: Date;
    title: string;
    trackNumber: number;
    type: any;
  }

  interface SetQueueOptions {
    album?: string;
    items?: MediaItem[] | string[];
    parameters?: QueryParameters;
    playlist?: string;
    song?: string;
    songs?: string[];
    startPosition?: number;
    url?: string;
    startPlaying?: boolean;
    repeatMode?: boolean;
    startTime?: number;
  }

  /**
   * This object provides access to a player instance, and through the player
   * instance, access to control playback.
   */
  class MusicKitInstance {
    /**
     * An instance of the MusicKit API.
     */
    readonly api: API;
    /**
     * The developer token to identify yourself as a trusted developer and
     * member of the Apple Developer Program.
     */
    readonly developerToken: string;
    /**
     * A Boolean value indicating whether the user has authenticated and
     * authorized the application for use.
     */
    readonly isAuthorized: boolean;
    /**
     * A user token used to access personalized Apple Music content.
     */
    musicUserToken: string;
    /**
     * The current storefront for the configured MusicKit instance.
     */
    readonly storefrontId: string;
    readonly playbackState: PlaybackStates;

    restrictedEnabled: boolean;
    /**
     * Add an event listener for a MusicKit instance by name.
     *
     * @param name The name of the event.
     * @param callback The callback function to invoke when the event occurs.
     */
    addEventListener(name: string, callback: (event: any) => any): void;
    /**
     * Returns a promise containing a music user token when a user has
     * authenticated and authorized the app.
     */
    authorize(): Promise<string>;
    /**
     * Unauthorizes the app for the current user.
     */
    unauthorize(): Promise<void>;

    pause(): void;

    play(): Promise<number>;
    /**
     * Removes an event listener for a MusicKit instance by name.
     *
     * @param name The name of the event.
     * @param callback The callback function to remove.
     */
    removeEventListener(name: string, callback: (event: any) => any): void;
    /**
     * Sets the playback point to a specified time in seconds.
     *
     * @param time The time in seconds to set as the playback point.
     */
    seekToTime(time: number): Promise<any>;
    /**
     * Sets a music player's playback queue using queue options.
     *
     * @param options The option used to set the playback queue.
     */
    setQueue(options: SetQueueOptions): Promise<any>;

    stop(): void;
    volume: number;
  }

  declare type NowPlayingItem = {
    item?: MusicKit.MediaItem;
  };

  declare type PlayerPlaybackTime = {
    currentPlaybackDuration: number;
    currentPlaybackTime: number;
    currentPlaybackTimeRemaining: number;
  };

  declare type PlayerDurationTime = {
    duration: number;
  };

  declare type PlayerPlaybackState = {
    oldState: MusicKit.PlaybackStates;
    state: MusicKit.PlaybackStates;
    nowPlayingItem?: MusicKit.MediaItem;
  };
}
