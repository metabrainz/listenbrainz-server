/* eslint-disable */
// TODO: Make the code ESLint compliant
// TODO: Port to typescript

export default class Scrobble {
  constructor(rootScrobbleElement) {
    this.rootScrobbleElement = rootScrobbleElement;
  }

  lastfmID() {
    /* Returns url of type "http://www.last.fm/music/Mot%C3%B6rhead" */
    if (
      "url" in this.rootScrobbleElement &&
      this.rootScrobbleElement.url !== ""
    ) {
      let { url } = this.rootScrobbleElement;
      url = url.split("/");
      return url.slice(0, parts.length - 2).join("/");
    }
    return "";
  }

  artistName() {
    /* Returns artistName if present, else returns an empty string */
    if (
      "artist" in this.rootScrobbleElement &&
      "#text" in this.rootScrobbleElement.artist
    ) {
      return this.rootScrobbleElement.artist["#text"];
    }
    return "";
  }

  artistMBID() {
    /* Returns artistName if present, else returns an empty string */
    if (
      "artist" in this.rootScrobbleElement &&
      "mbid" in this.rootScrobbleElement.artist
    ) {
      return this.rootScrobbleElement.artist.mbid;
    }
    return "";
  }

  trackName() {
    /* Returns trackName if present, else returns an empty string */
    if ("name" in this.rootScrobbleElement) {
      return this.rootScrobbleElement.name;
    }
    return "";
  }

  releaseName() {
    /* Returns releaseName if present, else returns an empty string */
    if (
      "album" in this.rootScrobbleElement &&
      "#text" in this.rootScrobbleElement.album
    ) {
      return this.rootScrobbleElement.album["#text"];
    }
    return "";
  }

  releaseMBID() {
    /* Returns releaseMBID if present, else returns an empty string */
    if (
      "album" in this.rootScrobbleElement &&
      "mbid" in this.rootScrobbleElement.album
    ) {
      return this.rootScrobbleElement.album.mbid;
    }
    return "";
  }

  scrobbledAt() {
    /* Returns scrobbledAt if present, else returns an empty string */
    if (
      "date" in this.rootScrobbleElement &&
      "uts" in this.rootScrobbleElement.date
    ) {
      return this.rootScrobbleElement.date.uts;
    }
    /*
      The audioscrobbler API's output differs when the user is playing song.
      In case, when the user is playing song, the API returns 1st listen with
      attribute as {"@attr": {"now_playing":"true"}} while other listens with
      attribute as {"date": {"utc":"12345756", "#text":"21 Jul 2016, 10:22"}}
      We need to only submit listens which were played in the past.
      */
    return "";
  }

  trackMBID() {
    /* Returns trackMBID if present, else returns an empty string */
    if ("mbid" in this.rootScrobbleElement) {
      return this.rootScrobbleElement.mbid;
    }
    return "";
  }

  asJSONSerializable() {
    const trackjson = {
      track_metadata: {
        track_name: this.trackName(),
        artist_name: this.artistName(),
        release_name: this.releaseName(),
        additional_info: {
          listening_from: "lastfm",
          recording_mbid: this.trackMBID(),
          lastfm_release_mbid: this.releaseMBID(),
          lastfm_artist_mbid: this.artistMBID(),
        },
      },
      listened_at: this.scrobbledAt(),
    };

    // Remove keys with blank values
    (function filter(obj) {
      Object.keys(obj).forEach(function (key) {
        let value = obj[key];
        if (value === "" || value === null) {
          delete obj[key];
        } else if (
          Object.prototype.toString.call(value) === "[object Object]"
        ) {
          filter(value);
        } else if (Array.isArray(value)) {
          value = value.filter(Boolean);
          obj[key] = value;
          value.forEach(function (el) {
            filter(el);
          });
        }
      });
    })(trackjson);
    return trackjson;
  }
}
