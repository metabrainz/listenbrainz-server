// Older implementations and Safari use the deprecated callback signature of Notification.requestPermission
// This util allows us to detect if the Promise-based signature is available
function checkNotificationPromise() {
  try {
    Notification.requestPermission().then();
  } catch (e) {
    return false;
  }

  return true;
}

export function hasNotificationSupport(): boolean {
  if (!("Notification" in window)) {
    return false;
  }
  return true;
}

export async function hasNotificationPermission(): Promise<boolean> {
  try {
    // Does the browser support notifications?
    if (!hasNotificationSupport) {
      return false;
    }
    // If the permission has been explicitly granted we're all done
    if (window.Notification.permission === "granted") {
      return true;
    }
    // If the permission has been explicitly denied, don't request it again
    if (window.Notification.permission === "denied") {
      return false;
    }
    // In other cases we can request permissions
    // If the Notifications implementation supports promises, request it that way
    if (checkNotificationPromise()) {
      const permission = await window.Notification.requestPermission();
      return permission === "granted";
    }
    // Otherwise use the deprecated callback signature
    return new Promise((resolve) => {
      window.Notification.requestPermission((permission) => {
        resolve(permission === "granted");
      });
    });
  } catch (error) {
    return false;
  }
}

export function createNotification(
  title: string,
  artist?: string,
  album?: string,
  icon?: any
) {
  if (hasNotificationSupport()) {
    const body = `${artist ?? ""}${album ? ` — ${album}` : ""}`;
    const notification = new Notification(title, {
      body,
      icon,
    });
  }
}

/**
 * The MediaSession API allows us to communicate with the native browser or device media control
 */

export function hasMediaSessionSupport(): boolean {
  if ("mediaSession" in window.navigator) {
    return true;
  }
  return false;
}

/* Our players (youtube, spotify, etc.) are usually loaded in an iFrame,
 * which use the MediaSession themselves. CORS policy prevents us from modifying it.
 * In order to make the media controls (forward/next controls BrainzPlayer instead of embeddded player) work the way we want,
 * we need to replace the iframe MediaSession with our own (trick from https://stackoverflow.com/a/65434258)
 */
export function hijackMediaSession(
  prevTrackCallback: Function,
  nextTrackCallback: Function,
  seekBackwardCallback: Function,
  seekForwardCallback: Function
): void {
  if (!hasMediaSessionSupport()) {
    return;
  }
  const { mediaSession } = window.navigator;
  mediaSession.metadata = new window.MediaMetadata({});
  // Placeholder audio element is required in order for browser to recognize
  // a media is playing and allow notifications
  const audioElement = new Audio("/static/sound/5-seconds-of-silence.mp3");
  audioElement.loop = true;
  audioElement.volume = 0;
  // this requires the user already interacted with your page
  audioElement
    .play()
    .then(() => {
      // We only need to override these handlers.
      // Play/pause should be managed appropriately by the original MediaSession.
      mediaSession.setActionHandler("previoustrack", (e) => {
        prevTrackCallback();
      });
      mediaSession.setActionHandler("nexttrack", (e) => {
        nextTrackCallback();
      });
      mediaSession.setActionHandler("seekbackward", (e) => {
        seekBackwardCallback();
      });
      mediaSession.setActionHandler("seekforward", (e) => {
        seekForwardCallback();
      });
    })
    // eslint-disable-next-line no-console
    .catch(console.warn);
}

export function updateMediaSession(
  title: string,
  artist?: string,
  album?: string,
  artwork?: Array<MediaImage>
): void {
  if (!hasMediaSessionSupport()) {
    return;
  }
  window.navigator.mediaSession.metadata = new window.MediaMetadata({
    title,
    artist,
    album,
    artwork,
  });
}
