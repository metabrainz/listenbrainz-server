/* jshint esversion: 6 */
/* jshint strict:false */

function submit_music_user_token(
  developer_token,
  music_user_token,
  expires_at
) {
  fetch("/profile/music-services/apple/submit-token/", {
    method: "POST",
    redirect: "manual",
    headers: {
      "Content-Type": "application/json;charset=UTF-8",
    },
    body: JSON.stringify({ developer_token, music_user_token, expires_at }),
  }).then((_) => {
    window.location.reload();
  });
}

function music_kit_loaded_listener(token) {
  const configuration = {
    developerToken: token.access_token,
    debug: true,
    app: {
      name: "ListenBrainz",
      build: "latest",
    },
  };
  return function listener() {
    window.MusicKit.configure(configuration).then((_) => {
      const instance = window.MusicKit.getInstance();
      instance
        .authorize()
        .then((music_user_token) =>
          submit_music_user_token(
            token.access_token,
            music_user_token,
            token.expires_at
          )
        );
    });
  };
}

function load_apple_music_script(developer_token) {
  const listener = music_kit_loaded_listener(developer_token);
  window.addEventListener("musickitloaded", listener);
  const el = document.createElement("script");
  const container = document.head || document.body;
  el.type = "text/javascript";
  el.async = true;
  el.src = "https://js-cdn.music.apple.com/musickit/v3/musickit.js";
  container.appendChild(el);
}

function start_linking_apple_music(value) {
  if (value === "listen") {
    fetch("/profile/music-services/apple/get-token/")
      .then((response) => response.json())
      .then((response) => response.token)
      .then((token) => load_apple_music_script(token));
  } else {
    fetch("/profile/music-services/apple/disconnect/", {
      method: "POST",
      redirect: "manual",
    }).then((_) => {
      window.location.reload();
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("apple-music-form");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
  });
});
