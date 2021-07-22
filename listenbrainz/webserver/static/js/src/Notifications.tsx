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

// On Chrome for Android, the new Notification(…) constructor is not supported and throws an error
// We can use this utility (from https://bugs.chromium.org/p/chromium/issues/detail?id=481856)
// to detect if we can use the constructor. The alternative is to use ServiceWorkers, but that seems a bit overkill and cumbersome.
function isNewNotificationConstructorSupported() {
  if (!window.Notification || !window.Notification.requestPermission)
    return false;
  if (window.Notification.permission === "granted")
    throw new Error(
      "You must only call this *before* calling Notification.requestPermission(), otherwise this feature detect would bug the user with an actual notification!"
    );
  try {
    const fakeNotification = new window.Notification("");
  } catch (e) {
    if (e.name === "TypeError") return false;
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
    if (!hasNotificationSupport()) {
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
    // We use this utility to determine if we can use `new Notification()`. If so, we ask for permission
    if (isNewNotificationConstructorSupported()) {
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
    }
    return false;
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

// This method is called on each track change; I don't have a better idea for destroying the Audio objects we create
let placeholderAudioElement;
export function overwriteMediaSession(
  actionHandlers: Array<{
    action: string;
    handler: () => void;
  }>
): void {
  if (!hasMediaSessionSupport()) {
    return;
  }
  const { mediaSession } = window.navigator;
  mediaSession.metadata = new window.MediaMetadata({});
  // Placeholder audio element is required in order for browser to recognize
  // a media is playing and allow notifications and to later overwrite the MediaSession
  placeholderAudioElement = null;
  placeholderAudioElement = new Audio("/static/sound/5-seconds-of-silence.mp3");
  placeholderAudioElement.loop = true;
  placeholderAudioElement.volume = 0;
  placeholderAudioElement
    .play()
    .then(() => {
      // We only need to override prev/next and seek forward/backward handlers.
      // Play/pause should be managed appropriately by the original MediaSession.
      // Certain handlers might not be supported so we wrap each call in a try/catch
      actionHandlers.forEach(({ action, handler }) => {
        try {
          navigator.mediaSession.setActionHandler(action, (actionDetails) => {
            handler();
          });
        } catch (error) {
          console.log(
            `The media session action "${action}" is not supported yet.`
          );
        }
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
