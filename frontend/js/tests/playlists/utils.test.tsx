import {
  JSPFTrackToListen,
  MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION,
  MUSICBRAINZ_JSPF_TRACK_EXTENSION,
  PLAYLIST_ARTIST_URI_PREFIX,
  PLAYLIST_TRACK_URI_PREFIX,
  PLAYLIST_URI_PREFIX,
  getArtistMBIDFromURI,
  getPlaylistExtension,
  getPlaylistId,
  getRecordingMBIDFromJSPFTrack,
  getTrackExtension,
  isPlaylistOwner,
  listenToJSPFTrack,
  millisecondsToStr,
} from "../../src/playlists/utils";

const playlistMBID = "4245ccd3-4f0d-4276-95d6-2e09d87b5546";
const recordingMBID = "c0a1fc94-5f04-4a5f-bc09-e5de0c49cd12";
const artistMBID = "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11";

const playlistExtension: JSPFPlaylistExtension = {
  public: true,
  collaborators: ["alice"],
};

const playlist: JSPFPlaylist = {
  title: "My playlist",
  creator: "iliekcomputers",
  identifier: `${PLAYLIST_URI_PREFIX}${playlistMBID}`,
  date: "2021-01-01T00:00:00Z",
  track: [],
  extension: {
    [MUSICBRAINZ_JSPF_PLAYLIST_EXTENSION]: playlistExtension,
  },
};

const trackExtension: JSPFTrackExtension = {
  added_by: "iliekcomputers",
  added_at: "2021-01-02T00:00:00Z",
  artist_identifiers: [`${PLAYLIST_ARTIST_URI_PREFIX}${artistMBID}`],
  additional_metadata: {
    caa_id: 12345,
    caa_release_mbid: "a5c0e1b8-4a0a-4c1b-9e45-1e2f3a4b5c6d",
    artists: [
      {
        artist_credit_name: "Portishead",
        artist_mbid: artistMBID,
        join_phrase: "",
      },
    ],
  },
};

const track: JSPFTrack = {
  identifier: `${PLAYLIST_TRACK_URI_PREFIX}${recordingMBID}`,
  title: "Glory Box",
  creator: "Portishead",
  album: "Dummy",
  duration: 306000,
  location: ["https://example.com/glory-box"],
  extension: {
    [MUSICBRAINZ_JSPF_TRACK_EXTENSION]: trackExtension,
  },
};

describe("isPlaylistOwner", () => {
  it("returns true when the user created the playlist", () => {
    expect(isPlaylistOwner(playlist, { name: "iliekcomputers" })).toBe(true);
  });

  it("returns false for another user", () => {
    expect(isPlaylistOwner(playlist, { name: "alice" })).toBe(false);
  });

  it("returns false when there is no user", () => {
    expect(
      isPlaylistOwner(playlist, (undefined as unknown) as ListenBrainzUser)
    ).toBe(false);
  });
});

describe("getPlaylistExtension", () => {
  it("returns the MusicBrainz playlist extension", () => {
    expect(getPlaylistExtension(playlist)).toEqual(playlistExtension);
  });

  it("returns null when the playlist has no extension", () => {
    expect(getPlaylistExtension({ ...playlist, extension: undefined })).toBe(
      null
    );
  });

  it("returns null when the playlist is undefined", () => {
    expect(getPlaylistExtension(undefined)).toBe(null);
  });
});

describe("getTrackExtension", () => {
  it("returns the MusicBrainz track extension", () => {
    expect(getTrackExtension(track)).toEqual(trackExtension);
  });

  it("returns null when the track has no extension", () => {
    expect(getTrackExtension({ ...track, extension: undefined })).toBe(null);
  });

  it("returns null when the track is undefined", () => {
    expect(getTrackExtension(undefined)).toBe(null);
  });
});

describe("getPlaylistId", () => {
  it("strips the playlist URI prefix", () => {
    expect(getPlaylistId(playlist)).toEqual(playlistMBID);
  });

  it("returns an empty string when the playlist is undefined", () => {
    expect(getPlaylistId(undefined)).toEqual("");
  });

  it("returns an empty string when the playlist has no identifier", () => {
    expect(
      getPlaylistId({
        ...playlist,
        identifier: (undefined as unknown) as string,
      })
    ).toEqual("");
  });
});

describe("getRecordingMBIDFromJSPFTrack", () => {
  it("extracts the MBID from a string identifier", () => {
    expect(getRecordingMBIDFromJSPFTrack(track)).toEqual(recordingMBID);
  });

  it("finds the MusicBrainz identifier in an array of identifiers", () => {
    expect(
      getRecordingMBIDFromJSPFTrack({
        ...track,
        identifier: [
          "https://example.com/some-other-id",
          `${PLAYLIST_TRACK_URI_PREFIX}${recordingMBID}`,
        ],
      })
    ).toEqual(recordingMBID);
  });

  it("returns an empty string when no identifier is a MusicBrainz recording", () => {
    expect(
      getRecordingMBIDFromJSPFTrack({
        ...track,
        identifier: ["https://example.com/some-other-id"],
      })
    ).toEqual("");
  });

  it("returns an empty string when the identifier is missing", () => {
    expect(
      getRecordingMBIDFromJSPFTrack({
        ...track,
        identifier: (undefined as unknown) as string,
      })
    ).toEqual("");
  });
});

describe("getArtistMBIDFromURI", () => {
  it("strips the artist URI prefix", () => {
    expect(
      getArtistMBIDFromURI(`${PLAYLIST_ARTIST_URI_PREFIX}${artistMBID}`)
    ).toEqual(artistMBID);
  });

  it("returns an empty string for an undefined URI", () => {
    expect(getArtistMBIDFromURI((undefined as unknown) as string)).toEqual("");
  });
});

describe("millisecondsToStr", () => {
  it("formats zero", () => {
    expect(millisecondsToStr(0)).toEqual("0:00");
  });

  it("formats less than a minute", () => {
    expect(millisecondsToStr(5000)).toEqual("0:05");
    expect(millisecondsToStr(59000)).toEqual("0:59");
  });

  it("formats whole minutes", () => {
    expect(millisecondsToStr(60000)).toEqual("1:00");
    expect(millisecondsToStr(306000)).toEqual("5:06");
  });

  it("ignores leftover milliseconds", () => {
    expect(millisecondsToStr(61999)).toEqual("1:01");
  });

  it("does not show hours under one hour", () => {
    expect(millisecondsToStr(3599000)).toEqual("59:59");
  });

  it("formats durations of one hour or more", () => {
    expect(millisecondsToStr(3600000)).toEqual("1:00:00");
    expect(millisecondsToStr(3723000)).toEqual("1:02:03");
  });
});

describe("JSPFTrackToListen", () => {
  it("converts a JSPF track to a listen", () => {
    expect(JSPFTrackToListen(track)).toEqual({
      listened_at: 0,
      listened_at_iso: "2021-01-02T00:00:00Z",
      user_name: "iliekcomputers",
      track_metadata: {
        artist_name: "Portishead",
        track_name: "Glory Box",
        release_name: "Dummy",
        additional_info: {
          duration_ms: 306000,
          recording_mbid: recordingMBID,
          origin_url: "https://example.com/glory-box",
          artist_mbids: [artistMBID],
        },
        mbid_mapping: {
          artist_mbids: [artistMBID],
          artists: trackExtension.additional_metadata?.artists,
          recording_mbid: recordingMBID,
          release_mbid: "a5c0e1b8-4a0a-4c1b-9e45-1e2f3a4b5c6d",
          caa_id: 12345,
          caa_release_mbid: "a5c0e1b8-4a0a-4c1b-9e45-1e2f3a4b5c6d",
        },
      },
    });
  });

  it("handles a track without the MusicBrainz extension", () => {
    const listen = JSPFTrackToListen({
      identifier: `${PLAYLIST_TRACK_URI_PREFIX}${recordingMBID}`,
      title: "Glory Box",
      creator: "Portishead",
    });
    expect(listen.user_name).toBeUndefined();
    expect(listen.listened_at_iso).toBeUndefined();
    expect(listen.track_metadata.mbid_mapping?.artist_mbids).toEqual([]);
    expect(listen.track_metadata.mbid_mapping?.artists).toEqual([]);
    expect(listen.track_metadata.additional_info?.recording_mbid).toEqual(
      recordingMBID
    );
    expect(listen.track_metadata.additional_info?.origin_url).toBeUndefined();
  });
});

describe("listenToJSPFTrack", () => {
  const listen: Listen = {
    listened_at: 1620000000,
    track_metadata: {
      artist_name: "Portishead",
      track_name: "Glory Box",
      release_name: "Dummy",
      additional_info: {
        recording_mbid: recordingMBID,
        duration_ms: 306000,
        origin_url: "https://example.com/glory-box",
      },
    },
  };

  it("converts a listen to a JSPF track", () => {
    expect(listenToJSPFTrack(listen)).toEqual({
      identifier: `${PLAYLIST_TRACK_URI_PREFIX}${recordingMBID}`,
      id: recordingMBID,
      title: "Glory Box",
      creator: "Portishead",
      album: "Dummy",
      duration: 306000,
      location: ["https://example.com/glory-box"],
    });
  });

  it("leaves optional fields undefined when missing", () => {
    const jspfTrack = listenToJSPFTrack({
      listened_at: 1620000000,
      track_metadata: {
        artist_name: "Portishead",
        track_name: "Glory Box",
        additional_info: { recording_mbid: recordingMBID },
      },
    });
    expect(jspfTrack.album).toBeUndefined();
    expect(jspfTrack.duration).toBeUndefined();
    expect(jspfTrack.location).toBeUndefined();
  });

  it("round-trips through JSPFTrackToListen", () => {
    const roundTripped = JSPFTrackToListen(listenToJSPFTrack(listen));
    expect(roundTripped.track_metadata.track_name).toEqual("Glory Box");
    expect(roundTripped.track_metadata.artist_name).toEqual("Portishead");
    expect(roundTripped.track_metadata.release_name).toEqual("Dummy");
    expect(roundTripped.track_metadata.additional_info?.recording_mbid).toEqual(
      recordingMBID
    );
  });

  // Documents current behaviour: without a recording MBID the identifier
  // ends in "undefined" rather than being left out
  it("builds an identifier ending in 'undefined' when there is no recording MBID", () => {
    const jspfTrack = listenToJSPFTrack({
      listened_at: 1620000000,
      track_metadata: { artist_name: "Portishead", track_name: "Glory Box" },
    });
    expect(jspfTrack.identifier).toEqual(
      `${PLAYLIST_TRACK_URI_PREFIX}undefined`
    );
    expect(jspfTrack.id).toBeUndefined();
  });
});
