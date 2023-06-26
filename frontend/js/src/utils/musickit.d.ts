// eslint-disable-next-line max-classes-per-file
interface Window {
  MusicKit: typeof MusicKit.MusicKitInstance;
}

declare namespace MusicKit {
  /**
   * This class represents the Apple Music API.
   */
  interface API {
    /**
     * Search the catalog using a query.
     *
     * @param term The term to search.
     * @param parameters A query parameters object that is serialized and passed
     * directly to the Apple Music API.
     */
    search(term: string, parameters?: QueryParameters): Promise<Resource[]>;
  }

  interface Resource {
    [key: string]: any;
  }

  interface QueryParameters {
    [key: string]: any;
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
   * A class that describes an error that may occur when using MusicKit JS,
   * including server and local errors.
   */
  class MKError extends Error {
    /**
     * The error code for this error.
     */
    errorCode: string;
    /**
     * A description of the error that occurred.
     */
    description?: string;
    /**
     * Error code indicating that you don't have permission to access the
     * endpoint, media item, or content.
     */
    static ACCESS_DENIED: string;
    /**
     * Error code indicating the authorization was rejected.
     */
    static AUTHORIZATION_ERROR: string;
    /**
     * Error code indicating a MusicKit JS configuration error.
     */
    static CONFIGURATION_ERROR: string;
    /**
     * Error code indicating you don't have permission to access this content,
     * due to content restrictions.
     */
    static CONTENT_RESTRICTED: string;
    /**
     * Error code indicating the parameters provided for this method are invalid.
     */
    static INVALID_ARGUMENTS: string;
    /**
     * Error code indicating that the VM certificate could not be applied.
     */
    static MEDIA_CERTIFICATE: string;
    /**
     * Error code indicating that the media item descriptor is invalid.
     */
    static MEDIA_DESCRIPTOR: string;
    /**
     * Error code indicating that a DRM key could not be generated.
     */
    static MEDIA_KEY: string;
    /**
     * Error code indicating a DRM license error.
     */
    static MEDIA_LICENSE: string;
    /**
     * Error code indicating a media playback error.
     */
    static MEDIA_PLAYBACK: string;
    /**
     * Error code indicating that an EME session could not be created.
     */
    static MEDIA_SESSION: string;
    /**
     * Error code indicating a network error.
     */
    static NETWORK_ERROR: string;
    /**
     * Error code indicating that the resource was not found.
     */
    static NOT_FOUND: string;
    /**
     * Error code indicating that you have exceeded the Apple Music API quota.
     */
    static QUOTA_EXCEEDED: string;
    static SERVER_ERROR: string;
    /**
     * Error code indicating the MusicKit service could not be reached.
     */
    static SERVICE_UNAVAILABLE: string;
    /**
     * Error code indicating that the user's Apple Music subscription has expired.
     */
    static SUBSCRIPTION_ERROR: string;
    /**
     * Error code indicating an unknown error.
     */
    static UNKNOWN_ERROR: string;
    /**
     * Error code indicating that the operation is not supported.
     */
    static UNSUPPORTED_ERROR: string;
  }

  /**
   * An array of media items to be played.
   */
  interface Queue {
    /**
     * A Boolean value indicating whether the queue has no items.
     */
    readonly isEmpty: boolean;
    /**
     * An array of all the media items in the queue.
     */
    readonly items: MediaItem[];
    /**
     * The number of items in the queue.
     */
    readonly length: number;
    /**
     * The next playable media item in the queue.
     */
    readonly nextPlayableItem?: MediaItem;
    /**
     * The current queue position.
     */
    readonly position: number;
    /**
     * The previous playable media item in the queue.
     */
    readonly previousPlayableItem?: MediaItem;

    /**
     * Add an event listener for a MusicKit queue by name.
     *
     * @param name The name of the event.
     * @param callback The callback function to remove.
     */
    addEventListener(name: string, callback: () => any): void;
    /**
     * Inserts the media items defined by the queue descriptor after the last
     * media item in the current queue.
     */
    append(descriptor: descriptor): void;
    /**
     * Returns the index in the playback queue for a media item descriptor.
     *
     * @param descriptor A descriptor can be an instance of the MusicKit.MediaItem
     * class, or a string identifier.
     */
    indexForItem(descriptor: descriptor): number;
    /**
     * Returns the media item located in the indicated array index.
     */
    item(index: number): MediaItem | null | undefined;
    /**
     * Inserts the media items defined by the queue descriptor into the current
     * queue immediately after the currently playing media item.
     */
    prepend(descriptor: any): void;
    /**
     * Removes an event listener for a MusicKit queue by name.
     *
     * @param name The name of the event.
     * @param callback The callback function to remove.
     */
    removeEventListener(name: string, callback: () => any): void;
  }

  /**
   * A media player that represents the media player for a MusicKit instance.
   */
  interface Player {
    /**
     * The current bit rate of the music player.
     */
    readonly bitrate: number;
    /**
     * The music player has EME loaded.
     */
    readonly canSupportDRM: boolean;
    /**
     * The current playback duration.
     */
    readonly currentPlaybackDuration: number;
    /**
     * The current playback progress.
     */
    readonly currentPlaybackProgress: number;
    /**
     * The current position of the playhead.
     */
    readonly currentPlaybackTime: number;
    /**
     * No description available.
     */
    readonly currentPlaybackTimeRemaining: number;
    /**
     * The current playback duration in hours and minutes.
     */
    readonly formattedCurrentPlaybackDuration: FormattedPlaybackDuration;
    /**
     * A Boolean value indicating whether the player is currently playing.
     */
    readonly isPlaying: boolean;
    /**
     * The currently-playing media item, or the media item, within an queue,
     * that you have designated to begin playback.
     */
    readonly nowPlayingItem: MediaItem;
    /**
     * The index of the now playing item in the current playback queue.
     */
    readonly nowPlayingItemIndex?: number;
    /**
     * The current playback rate for the player.
     */
    readonly playbackRate: number;
    /**
     * The current playback state of the music player.
     */
    readonly playbackState: PlaybackStates;
    /**
     * A Boolean value that indicates whether a playback target is available.
     */
    readonly playbackTargetAvailable?: boolean;
    /**
     * The current playback queue of the music player.
     */
    readonly queue: Queue;
    /**
     * The current repeat mode of the music player.
     */
    repeatMode: PlayerRepeatMode;
    /**
     * The current shuffle mode of the music player.
     */
    shuffleMode: PlayerShuffleMode;
    /**
     * A number indicating the current volume of the music player.
     */
    volume: number;
    /**
     * Adds an event listener as a callback for an event name.
     *
     * @param name The name of the event.
     * @param callback The callback function to invoke when the event occurs.
     */
    addEventListener(name: string, callback: () => any): void;
    /**
     * Begins playing the media item at the specified index in the queue immediately.
     *
     * @param index The queue index to begin playing media.
     */
    changeToMediaAtIndex(index: number): Promise<MediaItemPosition>;
    /**
     * Begins playing the media item in the queue immediately.
     *
     * @param descriptor descriptor can be a MusicKit.MediaItem instance or a
     * string identifier.
     */
    changeToMediaItem(descriptor: descriptor): Promise<MediaItemPosition>;
    /**
     * Sets the volume to 0.
     */
    mute(): void;
    /**
     * Pauses playback of the current item.
     */
    pause(): void;
    /**
     * Initiates playback of the current item.
     */
    play(): Promise<MediaItemPosition>;
    /**
     * Prepares a music player for playback.
     *
     * @param descriptor descriptor can be a MusicKit.MediaItem instance or a
     * string identifier.
     */
    prepareToPlay(descriptor: descriptor): Promise<void>;
    /**
     * No description available.
     *
     * @param name The name of the event.
     * @param callback The callback function to remove.
     */
    removeEventListener(name: string, callback: () => any): void;
    /**
     * Sets the playback point to a specified time.
     *
     * @param time The time to set as the playback point.
     */
    seekToTime(time: number): Promise<void>;
    /**
     * Displays the playback target picker if a playback target is available.
     */
    showPlaybackTargetPicker(): void;
    /**
     * Starts playback of the next media item in the playback queue.
     */
    skipToNextItem(): Promise<MediaItemPosition>;
    /**
     * Starts playback of the previous media item in the playback queue.
     */
    skipToPreviousItem(): Promise<MediaItemPosition>;
    /**
     * Stops the currently playing media item.
     */
    stop(): void;
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
   * The playback bit rate of the music player.
   */
  enum PlaybackBitrate {
    HIGH = 256,
    STANDARD = 64,
  }

  // enum is not exposed via the MusicKit namespace
  type PlayerRepeatMode = 0 | 1 | 2;

  // enum is not exposed via the MusicKit namespace
  type PlayerShuffleMode = 0 | 1;

  type MediaItemPosition = number;

  /**
   * This class represents a single media item.
   */
  class MediaItem {
    /**
     * A constructor that creates a new media item from specified options.
     */
    constructor(options?: MediaItemOptions);
    /**
     * Prepares a media item for playback.
     */
    prepareToPlay(): Promise<void>;
    /**
     * A string of information about the album.
     */
    readonly albumInfo: string;
    /**
     * The title of the album.
     */
    readonly albumName: string;
    /**
     * The artist for a media item.
     */
    readonly artistName: string;
    /**
     * The artwork object for the media item.
     */
    readonly artwork: Artwork;
    /**
     * The artwork image for the media item.
     */
    readonly artworkURL: string;
    /**
     * The attributes object for the media item.
     */
    readonly attributes: any;
    /**
     * A string containing the content rating for the media item.
     */
    readonly contentRating: string;
    /**
     * The disc number where the media item appears.
     */
    readonly discNumber: number;
    /**
     * The identifier for the media item.
     */
    readonly id: string;
    /**
     * A string of common information about the media item.
     */
    readonly info: string;
    /**
     * A Boolean value that indicates whether the item has explicit lyrics or language.
     */
    readonly isExplicitItem: boolean;
    /**
     * A Boolean value that indicated whether the item is playable.
     */
    readonly isPlayable: boolean;
    /**
     * A Boolean value indicating whether the media item is prepared to play.
     */
    readonly isPreparedToPlay: boolean;
    /**
     * The ISRC (International Standard Recording Code) for a media item.
     */
    readonly isrc: string;
    /**
     * The playback duration of the media item.
     */
    readonly playbackDuration: number;
    readonly playlistArtworkURL: string;
    readonly playlistName: string;
    /**
     * The URL to an unencrypted preview of the media item.
     */
    readonly previewURL: string;
    /**
     * The release date of the media item.
     */
    readonly releaseDate?: Date;
    /**
     * The name of the media item.
     */
    readonly title: string;
    /**
     * The number of the media item in the album's track list.
     */
    readonly trackNumber: number;
    /**
     * The type of the media item.
     */
    type: any;
  }

  /**
   * The options to use when defining a media item.
   */
  interface MediaItemOptions {
    /**
     * The attributes for the media item.
     */
    attributes?: any;
    /**
     * The identifier for the media item.
     */
    id?: string;
    /**
     * The type for the media item.
     */
    type?: any;
  }

  /**
   * This property describes a media item.
   */
  type descriptor = MediaItem | string;

  /**
   * The options to use when defining a media item.
   */
  interface MediaItemOptions {
    /**
     * The attributes for the media item.
     */
    attributes?: any;
    /**
     * The identifier for the media item.
     */
    id?: string;
    /**
     * The type for the media item.
     */
    type?: any;
  }


  interface SetQueueOptions {
    /**
     * The catalog album used to set a music player's playback queue.
     */
    album?: string;
    /**
     * The media items used to set a music player's playback queue.
     */
    items?: descriptor[];
    /**
     * The parameters used to set a music player's playback queue.
     */
    parameters?: QueryParameters;
    /**
     * The playlist used to set a music player's playback queue.
     */
    playlist?: string;
    /**
     * The song used to set a music player's playback queue.
     */
    song?: string;
    /**
     * The songs used to set a music player's playback queue.
     */
    songs?: string[];
    /**
     * The start position for a set playback queue.
     */
    startPosition?: number;
    /**
     * A content URL used to set a music player's playback queue.
     */
    url?: string;
    startPlaying?: boolean;
    repeatMode?: boolean;
    startTime?: number;
  }

  /**
   * This property describes a media item.
   */
  type descriptor = MediaItem | string;

  /**
   * This object provides access to a player instance, and through the player
   * instance, access to control playback.
   */
  interface MusicKitInstance {
    /**
     * An instance of the MusicKit API.
     */
    readonly api: API;
    /**
     * An instance of the MusicKit API.
     */
    readonly bitrate: PlaybackBitrate;
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
    readonly musicUserToken: string;
    /**
     * The current playback state of the music player.
     */
    readonly playbackState: PlaybackStates;
    /**
     * A Boolean value that indicates if a playback target is available.
     */
    readonly playbackTargetAvailable: boolean;
    /**
     * An instance of the MusicKit player.
     */
    readonly player: Player;
    /**
     * The current storefront for the configured MusicKit instance.
     */
    readonly storefrontId: string;
    /**
     * Add an event listener for a MusicKit instance by name.
     *
     * @param name The name of the event.
     * @param callback The callback function to invoke when the event occurs.
     */
    addEventListener(name: string, callback: () => any): void;
    /**
     * Returns a promise containing a music user token when a user has
     * authenticated and authorized the app.
     */
    authorize(): Promise<string>;
    /**
     * Begins playing the media item at the specified index in the queue.
     *
     * @param index The queue index to begin playing media.
     */
    changeToMediaAtIndex(index: number): Promise<number>;
    /**
     * Pauses playback of the media player.
     */
    pause(): void;
    /**
     * Begins playback of the current media item.
     */
    play(): Promise<MediaItemPosition>;
    /**
     * No description available.
     */
    playLater(options: SetQueueOptions): Promise<void>;
    /**
     * No description available.
     */
    playNext(options: SetQueueOptions): Promise<void>;
    /**
     * Removes an event listener for a MusicKit instance by name.
     *
     * @param name The name of the event.
     * @param callback The callback function to remove.
     */
    removeEventListener(name: string, callback: () => any): void;
    /**
     * Sets the playback point to a specified time.
     *
     * @param time The time to set as the playback point.
     */
    seekToTime(time: number): Promise<any>;
    /**
     * Sets a music player's playback queue using queue options.
     *
     * @param options The option used to set the playback queue.
     */
    setQueue(options: SetQueueOptions): Promise<Queue>;
    /**
     * Starts playback of the next media item in the playback queue.
     */
    skipToNextItem(): Promise<MediaItemPosition>;
    /**
     * Starts playback of the previous media item in the playback queue.
     */
    skipToPreviousItem(): Promise<MediaItemPosition>;
    /**
     * Stops playback of the media player.
     */
    stop(): void;
    /**
     * Unauthorizes the app for the current user.
     */
    unauthorize(): Promise<any>;
  }
}
