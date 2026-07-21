import { searchForSubsonicTrack } from "../../../src/common/brainzplayer/SubsonicPlayer";

describe("searchForSubsonicTrack", () => {
  const firstTrack: NavidromeTrack = {
    id: "first-track",
    title: "Wrong Song",
    artist: "Wrong Artist",
    album: "Wrong Album",
    albumId: "wrong-album",
    duration: 180,
  };

  const mbidMatchedTrack: NavidromeTrack = {
    id: "mbid-track",
    title: "Different Title",
    artist: "Different Artist",
    album: "Different Album",
    albumId: "different-album",
    duration: 181,
    musicBrainzId: "2cfad207-3f55-4aec-8120-86cf66e34d59",
  };

  const titleMatchedTrack: NavidromeTrack = {
    id: "title-track",
    title: "Target Song",
    artist: "Other Artist",
    album: "Other Album",
    albumId: "other-album",
    duration: 182,
  };

  const mockSubsonicSearchResponse = (songs: NavidromeTrack[]) => {
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: {
          get: () => "application/json",
        },
        json: () =>
          Promise.resolve({
            "subsonic-response": {
              status: "ok",
              searchResult3: {
                song: songs,
              },
            },
          }),
      });
    });
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("prefers a matching MusicBrainz ID over the first result", async () => {
    mockSubsonicSearchResponse([firstTrack, mbidMatchedTrack]);

    await expect(
      searchForSubsonicTrack(
        "https://test.navidrome.com",
        "u=test-user&t=test-token&s=test-salt&v=1.16.1&c=listenbrainz&f=json",
        "Target Song",
        "Target Artist",
        "2cfad207-3f55-4aec-8120-86cf66e34d59"
      )
    ).resolves.toEqual(mbidMatchedTrack);
  });

  it("falls back to a normalized exact title match", async () => {
    mockSubsonicSearchResponse([firstTrack, titleMatchedTrack]);

    await expect(
      searchForSubsonicTrack(
        "https://test.navidrome.com",
        "u=test-user&t=test-token&s=test-salt&v=1.16.1&c=listenbrainz&f=json",
        " target song ",
        "Target Artist"
      )
    ).resolves.toEqual(titleMatchedTrack);
  });

  it("uses a strict fuzzy title and artist match before falling back to the first result", async () => {
    const fuzzyMatchedTrack: NavidromeTrack = {
      id: "fuzzy-track",
      title: "Target Sogn",
      artist: "Target Artist",
      album: "Target Album",
      albumId: "target-album",
      duration: 183,
    };
    mockSubsonicSearchResponse([firstTrack, fuzzyMatchedTrack]);

    await expect(
      searchForSubsonicTrack(
        "https://test.navidrome.com",
        "u=test-user&t=test-token&s=test-salt&v=1.16.1&c=listenbrainz&f=json",
        "Target Song",
        "Target Artist"
      )
    ).resolves.toEqual(fuzzyMatchedTrack);
  });
});
