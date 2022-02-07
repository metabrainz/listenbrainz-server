/**
 * Older implementations and Safari use the deprecated callback signature
 * of Notification.requestPermission instead of the Promise-based signature
 * This util allows us to detect if the Promise-based signature is available.
 *  */
function checkNotificationPromise() {
  try {
    Notification.requestPermission().then();
  } catch (e) {
    return false;
  }

  return true;
}

/**
 * On Chrome for Android, the new Notification(…) constructor is not supported and throws an error.
 * We can use the following method to detect if we can use the constructor
 * (from https://bugs.chromium.org/p/chromium/issues/detail?id=481856).
 * The proper alternative is to use ServiceWorkers for notifications
 * instead of the Notification API, but that seems quite cumbersome.
 *  */
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
/**
 * Check if 1. Notification API can be used on this browser
 * 2. if the user has granted permission for notifications
 * 3. requests permission if it hasn't already been explicitly granted or denied
 * @returns a Promise that resolves to a boolean
 */
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
 * The MediaSession API allows us to communicate with the native browser or device media control.
 * Presence of navigator.mediaSession on the global window object is sufficient feature detection.
 */

export function hasMediaSessionSupport(): boolean {
  if ("mediaSession" in window.navigator) {
    return true;
  }
  return false;
}

/* Our embedded players (youtube, spotify, etc.) are  loaded in an iFrame,
 * which uses the MediaSession API themselves. CORS policy prevents us from modifying the existing MediaSession.
 * In order to make the media controls work the way we want (prev/next media keys controls BrainzPlayer),
 * we need to replace the iframe MediaSession with our own (trick from https://stackoverflow.com/a/65434258)
 */

/**
 * This method is called on each track change.
 * I don't have a better idea for destroying the Audio objects we create
 * than to store it in a global variable and `null` it before creating a new one.
 * They get garbage collected, I checked.
 */
let placeholderAudioElement;
/* eslint-disable no-console */
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
  // Playing an audio element >= 5s in length is required in order for the browser to recognize
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
          console.warn(
            `The media session action "${action}" is not supported yet.`,
            error
          );
        }
      });
    })
    .catch(console.warn);
}
/* eslint-enable no-console */

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

export function updateWindowTitle(
  trackName: string,
  prefix?: string,
  postfix?: string
) {
  if (window.document) {
    window.document.title = `${prefix || ""}${trackName}${postfix || ""}`;
  }
}
