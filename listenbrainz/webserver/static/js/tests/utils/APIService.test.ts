import APIService from "../../src/utils/APIService";

const feedProps = require("../__mocks__/feedProps.json");
const pinProps = require("../__mocks__/pinProps.json");

const apiService = new APIService("foobar");

// from https://github.com/kentor/flush-promises/blob/46f58770b14fb74ce1ff27da00837c7e722b9d06/index.js
const scheduler =
  typeof setImmediate === "function" ? setImmediate : setTimeout;

function flushPromises() {
  return new Promise(function flushPromisesPromise(resolve) {
    scheduler(resolve, 0);
  });
}

describe("submitListens", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
      });
    });
    jest.useFakeTimers();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.submitListens("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);
    expect(window.fetch).toHaveBeenCalledWith("foobar/1/submit-listens", {
      method: "POST",
      headers: {
        Authorization: "Token foobar",
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({
        listen_type: "import",
        payload: [
          {
            listened_at: 1000,
            track_metadata: {
              artist_name: "foobar",
              track_name: "bazfoo",
            },
          },
        ],
      }),
    });
  });

  it("retries if network error / submit fails", async () => {
    // Overide mock for fetch:
    window.fetch = jest
      .fn()
      .mockImplementationOnce(() => {
        // 1st call will recieve a network error
        return Promise.reject(new Error("Oh no!"));
      })
      .mockImplementation(() => {
        return Promise.resolve({
          ok: true,
          status: 200,
        });
      });
    const spy = jest.spyOn(apiService, "submitListens");
    apiService.submitListens("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);

    // The infamous flush promises sandwich
    await flushPromises();
    jest.runAllTimers();
    await flushPromises();

    expect(setTimeout).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy).toHaveBeenNthCalledWith(
      2,
      "foobar",
      "import",
      [
        {
          listened_at: 1000,
          track_metadata: {
            artist_name: "foobar",
            track_name: "bazfoo",
          },
        },
      ],
      2
    );
  });

  it("retries if error 429 is recieved (rate limited)", async () => {
    // Overide mock for fetch
    window.fetch = jest
      .fn()
      .mockImplementationOnce(() => {
        // 1st call will recieve a 429 error
        return Promise.resolve({
          ok: false,
          status: 429,
        });
      })
      .mockImplementation(() => {
        return Promise.resolve({
          ok: true,
          status: 200,
        });
      });
    const spy = jest.spyOn(apiService, "submitListens");
    apiService.submitListens("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);

    // The infamous flush promises sandwich
    await flushPromises();
    jest.runAllTimers();
    await flushPromises();

    expect(setTimeout).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy).toHaveBeenNthCalledWith(
      2,
      "foobar",
      "import",
      [
        {
          listened_at: 1000,
          track_metadata: {
            artist_name: "foobar",
            track_name: "bazfoo",
          },
        },
      ],
      2
    );
  });

  it("skips if any other response code is recieved", async () => {
    // Overide mock for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 404,
      });
    });
    const spy = jest.spyOn(apiService, "submitListens");
    await apiService.submitListens("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);
    expect(spy).toHaveBeenCalledTimes(1);
    expect(setTimeout).not.toHaveBeenCalled(); // should return response with no calls for additional retries
  });

  it("returns the response if successful", async () => {
    await expect(
      apiService.submitListens("foobar", "import", [
        {
          listened_at: 1000,
          track_metadata: {
            artist_name: "foobar",
            track_name: "bazfoo",
          },
        },
      ])
    ).resolves.toEqual({
      ok: true,
      status: 200,
    });
  });

  it("strips the listened_at field for playing_now listen", async () => {
    const fetchMock = jest.spyOn(window, "fetch");
    const listensToSubmit = [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ];
    // Expecting a payload without listened_at field, otherwise we get an error response
    const expectedBody = {
      listen_type: "playing_now",
      payload: [
        {
          track_metadata: {
            artist_name: "foobar",
            track_name: "bazfoo",
          },
        },
      ],
    };
    await apiService.submitListens("foobar", "playing_now", listensToSubmit);
    expect(fetchMock).toHaveBeenCalledWith(
      `${apiService.APIBaseURI}/submit-listens`,
      expect.objectContaining({
        body: JSON.stringify(expectedBody),
      })
    );
  });

  it("calls itself recursively if size of payload exceeds MAX_LISTEN_SIZE", async () => {
    apiService.MAX_LISTEN_SIZE = 100;

    const spy = jest.spyOn(apiService, "submitListens");
    await apiService.submitListens("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "bazfoo",
          track_name: "foobar",
        },
      },
    ]);
    expect(spy).toHaveBeenCalledTimes(3);
    expect(spy).toHaveBeenNthCalledWith(1, "foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "bazfoo",
          track_name: "foobar",
        },
      },
    ]);
    expect(spy).toHaveBeenNthCalledWith(
      2,
      "foobar",
      "import",
      [
        {
          listened_at: 1000,
          track_metadata: {
            artist_name: "foobar",
            track_name: "bazfoo",
          },
        },
      ],
      3
    );
    expect(spy).toHaveBeenNthCalledWith(
      3,
      "foobar",
      "import",
      [
        {
          listened_at: 1000,
          track_metadata: {
            artist_name: "bazfoo",
            track_name: "foobar",
          },
        },
      ],
      3
    );
  });
});

describe("getUserEntity", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ latest_import: "0" }),
      });
    });
  });

  it("calls fetch correctly when optional parameters are passed", async () => {
    await apiService.getUserEntity("foobar", "release", "all_time", 10, 5);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/releases?offset=10&range=all_time&count=5"
    );
  });

  it("calls fetch correctly when username is not passed", async () => {
    await apiService.getUserEntity(undefined, "release", "all_time", 10, 5);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/sitewide/releases?offset=10&range=all_time&count=5"
    );
  });

  it("calls fetch correctly when optional parameters are not passed", async () => {
    await apiService.getUserEntity("foobar", "artist");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/artists?offset=0&range=all_time"
    );
  });

  it("throws appropriate error if statistics haven't been calculated", async () => {
    window.fetch = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        status: 204,
        statusText: "NO CONTENT",
      });
    });

    await expect(apiService.getUserEntity("foobar", "artist")).rejects.toThrow(
      Error("HTTP Error NO CONTENT")
    );
  });

  it("calls checkStatus once", async () => {
    apiService.checkStatus = jest.fn();

    await apiService.getUserEntity("foobar", "release");
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });
});

describe("getUserListeningActivity", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ latest_import: "0" }),
      });
    });
  });

  it("calls fetch correctly when optional parameters are passed", async () => {
    await apiService.getUserListeningActivity("foobar", "week");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/listening-activity?range=week"
    );
  });

  it("calls fetch correctly when username is not passed", async () => {
    await apiService.getUserListeningActivity(undefined);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/sitewide/listening-activity?range=all_time"
    );
  });

  it("calls fetch correctly when optional parameters are not passed", async () => {
    await apiService.getUserListeningActivity("foobar");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/listening-activity?range=all_time"
    );
  });

  it("throws appropriate error if statistics haven't been calculated", async () => {
    window.fetch = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        status: 204,
        statusText: "NO CONTENT",
      });
    });

    await expect(apiService.getUserListeningActivity("foobar")).rejects.toThrow(
      Error("HTTP Error NO CONTENT")
    );
  });

  it("calls checkStatus once", async () => {
    apiService.checkStatus = jest.fn();

    await apiService.getUserListeningActivity("foobar");
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });
});

describe("getUserDailyActivity", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ latest_import: "0" }),
      });
    });
  });

  it("calls fetch correctly when optional parameters are passed", async () => {
    await apiService.getUserDailyActivity("foobar", "week");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/daily-activity?range=week"
    );
  });

  it("calls fetch correctly when optional parameters are not passed", async () => {
    await apiService.getUserDailyActivity("foobar");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/daily-activity?range=all_time"
    );
  });

  it("throws appropriate error if statistics haven't been calculated", async () => {
    window.fetch = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        status: 204,
        statusText: "NO CONTENT",
      });
    });

    await expect(apiService.getUserDailyActivity("foobar")).rejects.toThrow(
      Error("HTTP Error NO CONTENT")
    );
  });

  it("calls checkStatus once", async () => {
    apiService.checkStatus = jest.fn();

    await apiService.getUserDailyActivity("foobar");
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });
});

describe("getUserArtistMap", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ latest_import: "0" }),
      });
    });
  });

  it("calls fetch correctly when optional parameters are passed", async () => {
    await apiService.getUserArtistMap("foobar", "week", true);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/artist-map?range=week&force_recalculate=true"
    );
  });

  it("calls fetch correctly when optional parameters are not passed", async () => {
    await apiService.getUserArtistMap("foobar");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/artist-map?range=all_time&force_recalculate=false"
    );
  });

  it("calls fetch correctly when username is not passed", async () => {
    await apiService.getUserArtistMap(undefined);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/sitewide/artist-map?range=all_time&force_recalculate=false"
    );
  });

  it("throws appropriate error if statistics haven't been calculated", async () => {
    window.fetch = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        status: 204,
        statusText: "NO CONTENT",
      });
    });

    await expect(apiService.getUserArtistMap("foobar")).rejects.toThrow(
      Error("HTTP Error NO CONTENT")
    );
  });

  it("calls checkStatus once", async () => {
    apiService.checkStatus = jest.fn();

    await apiService.getUserArtistMap("foobar");
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });
});

describe("getUserListenCount", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ payload: { count: 42 } }),
      });
    });
  });

  it("calls fetch correctly", async () => {
    await apiService.getUserListenCount("fnord");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/user/fnord/listen-count",
      {
        method: "GET",
      }
    );
  });

  it("returns a number", async () => {
    const result = await apiService.getUserListenCount("fnord");
    expect(result).toEqual(42);
  });

  it("throws appropriate error if username is missing", async () => {
    await expect(apiService.getUserListenCount("")).rejects.toThrow(
      SyntaxError("Username missing")
    );
  });

  it("calls checkStatus once", async () => {
    apiService.checkStatus = jest.fn();

    await apiService.getUserListenCount("fnord");
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });
});

describe("getLatestImport", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ latest_import: "0" }),
      });
    });

    // Mock function for checkStatus
    apiService.checkStatus = jest.fn();
  });

  it("encodes url correctly", async () => {
    await apiService.getLatestImport("ईशान", "lastfm");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/latest-import?user_name=%E0%A4%88%E0%A4%B6%E0%A4%BE%E0%A4%A8&service=lastfm",
      {
        method: "GET",
      }
    );
  });

  it("calls checkStatus once", async () => {
    await apiService.getLatestImport("foobar", "lastfm");
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the latest import timestamp", async () => {
    await expect(
      apiService.getLatestImport("foobar", "lastfm")
    ).resolves.toEqual(0);
  });
});

describe("setLatestImport", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
      });
    });

    // Mock function for checkStatus
    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.setLatestImport("foobar", "lastfm", 0);
    expect(window.fetch).toHaveBeenCalledWith("foobar/1/latest-import", {
      method: "POST",
      headers: {
        Authorization: "Token foobar",
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ ts: 0, service: "lastfm" }),
    });
  });

  it("calls checkStatus once", async () => {
    await apiService.setLatestImport("foobar", "lastfm", 0);
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the response code if successful", async () => {
    await expect(
      apiService.setLatestImport("foobar", "lastfm", 0)
    ).resolves.toEqual(200);
  });
});

describe("submitFeedback", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
      });
    });

    // Mock function for checkStatus
    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.submitFeedback("foobar", 1, "foo", "foombid");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/feedback/recording-feedback",
      {
        method: "POST",
        headers: {
          Authorization: "Token foobar",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({
          score: 1,
          recording_msid: "foo",
          recording_mbid: "foombid",
        }),
      }
    );
  });

  it("fetches correclty if called with MBID only", async () => {
    await apiService.submitFeedback("foobar", 1, undefined, "foombid");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/feedback/recording-feedback",
      {
        method: "POST",
        headers: {
          Authorization: "Token foobar",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({ score: 1, recording_mbid: "foombid" }),
      }
    );
  });

  it("calls checkStatus once", async () => {
    await apiService.submitFeedback("foobar", 0, "foo");
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the response code if successful", async () => {
    await expect(
      apiService.submitFeedback("foobar", 0, "foo")
    ).resolves.toEqual(200);
  });
});

describe("getFeedbackForUserForRecordings", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ feedbacl: [] }),
      });
    });
  });

  it("calls fetch correctly", async () => {
    await apiService.getFeedbackForUserForRecordings(
      "foo",
      "bar,baz",
      "new,old"
    );
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/feedback/user/foo/get-feedback-for-recordings?recording_msids=bar,baz&recording_mbids=new,old"
    );
  });

  it("throws appropriate error if username is missing", async () => {
    await expect(apiService.getUserListenCount("")).rejects.toThrow(
      SyntaxError("Username missing")
    );
  });
});

describe("deleteListen", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
      });
    });

    // Mock function for checkStatus
    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.deleteListen("foobar", "foo", 0);
    expect(window.fetch).toHaveBeenCalledWith("foobar/1/delete-listen", {
      method: "POST",
      headers: {
        Authorization: "Token foobar",
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ listened_at: 0, recording_msid: "foo" }),
    });
  });

  it("calls checkStatus once", async () => {
    await apiService.deleteListen("foobar", "foo", 0);
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the response code if successful", async () => {
    await expect(apiService.deleteListen("foobar", "foo", 0)).resolves.toEqual(
      200
    );
  });
});

describe("getFeedForUser", () => {
  const payload = { ...feedProps };
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ payload }),
      });
    });

    // Mock function for checkStatus
    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.getFeedForUser("fnord", "shhh", 12345, undefined, 25);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/user/fnord/feed/events?min_ts=12345&count=25",
      {
        headers: {
          Authorization: "Token shhh",
        },
        method: "GET",
      }
    );
  });

  it("calls checkStatus once", async () => {
    await apiService.getFeedForUser("fnord", "shhh");
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the feed events array if successful", async () => {
    const events = await apiService.getFeedForUser("fnord", "shhh");
    expect(events).toBeDefined();
    expect(events).toEqual(payload.events);
  });

  it("throws appropriate error if username is missing", async () => {
    await expect(apiService.getFeedForUser("", "")).rejects.toThrow(
      SyntaxError("Username missing")
    );
  });
  it("throws appropriate error if userToken is missing", async () => {
    await expect(apiService.getFeedForUser("Cthulhu", "")).rejects.toThrow(
      SyntaxError("User token missing")
    );
  });
});

describe("recommendTrackToFollowers", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
      });
    });

    // Mock function for checkStatus
    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    const metadata: UserTrackRecommendationMetadata = {
      artist_name: "Hans Zimmer",
      track_name: "Flight",
      recording_msid: "recording_msid",
    };
    await apiService.recommendTrackToFollowers(
      "clark_kent",
      "auth_token",
      metadata
    );
    expect(window.fetch).toHaveBeenCalledWith(
      `foobar/1/user/clark_kent/timeline-event/create/recording`,
      {
        method: "POST",
        headers: {
          Authorization: "Token auth_token",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({ metadata }),
      }
    );
  });

  it("calls checkStatus once", async () => {
    const metadata: UserTrackRecommendationMetadata = {
      artist_name: "Hans Zimmer",
      track_name: "Flight",
      recording_msid: "recording_msid",
    };
    await apiService.recommendTrackToFollowers(
      "clark_kent",
      "auth_token",
      metadata
    );
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the response code if successful", async () => {
    const metadata: UserTrackRecommendationMetadata = {
      artist_name: "Hans Zimmer",
      track_name: "Flight",
      recording_msid: "recording_msid",
    };
    await expect(
      apiService.recommendTrackToFollowers("clark_kent", "auth_token", metadata)
    ).resolves.toEqual(200);
  });

  describe("submitPinRecording", () => {
    const pinnedRecordingFromAPI: PinnedRecording = {
      created: 1605927742,
      pinned_until: 1605927893,
      blurb_content:
        "Our perception of the passing of time is really just a side-effect of gravity",
      recording_mbid: "recording_mbid",
      row_id: 1,
      track_metadata: {
        artist_name: "TWICE",
        track_name: "Feel Special",
        additional_info: {
          release_mbid: "release_mbid",
          recording_msid: "recording_msid",
          recording_mbid: "recording_mbid",
          artist_msid: "artist_msid",
        },
      },
    };
    beforeEach(() => {
      // Mock function for fetch
      window.fetch = jest.fn().mockImplementation(() => {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => pinnedRecordingFromAPI,
        });
      });

      // Mock function for checkStatus
      apiService.checkStatus = jest.fn();
    });

    it("calls fetch with correct parameters", async () => {
      await apiService.submitPinRecording("foobar", "MSID", "MBID", "BLURB");
      expect(window.fetch).toHaveBeenCalledWith("foobar/1/pin", {
        method: "POST",
        headers: {
          Authorization: "Token foobar",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({
          recording_msid: "MSID",
          recording_mbid: "MBID",
          blurb_content: "BLURB",
        }),
      });
    });

    it("calls fetch with correct parameters when parameters are missing", async () => {
      await apiService.submitPinRecording("foobar", "MSID");
      expect(window.fetch).toHaveBeenCalledWith("foobar/1/pin", {
        method: "POST",
        headers: {
          Authorization: "Token foobar",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({ recording_msid: "MSID" }),
      });
    });

    it("calls checkStatus once", async () => {
      await apiService.submitPinRecording("foobar", "foo");
      expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
    });

    it("returns the json content if successful", async () => {
      await expect(
        apiService.submitPinRecording("foobar", "foo")
      ).resolves.toEqual(pinnedRecordingFromAPI);
    });
  });

  describe("unpinRecording", () => {
    beforeEach(() => {
      // Mock function for fetch
      window.fetch = jest.fn().mockImplementation(() => {
        return Promise.resolve({
          ok: true,
          status: 200,
        });
      });

      // Mock function for checkStatus
      apiService.checkStatus = jest.fn();
    });

    it("calls fetch with user token", async () => {
      await apiService.unpinRecording("foobar");
      expect(window.fetch).toHaveBeenCalledWith("foobar/1/pin/unpin", {
        method: "POST",
        headers: {
          Authorization: "Token foobar",
          "Content-Type": "application/json;charset=UTF-8",
        },
      });
    });

    it("calls checkStatus once", async () => {
      await apiService.unpinRecording("foobar");
      expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
    });

    it("returns the response code if successful", async () => {
      await expect(apiService.unpinRecording("foobar")).resolves.toEqual(200);
    });
  });

  describe("deletePin", () => {
    beforeEach(() => {
      // Mock function for fetch
      window.fetch = jest.fn().mockImplementation(() => {
        return Promise.resolve({
          ok: true,
          status: 200,
        });
      });

      // Mock function for checkStatus
      apiService.checkStatus = jest.fn();
    });

    it("calls fetch with correct parameters", async () => {
      await apiService.deletePin("foobar", 1337);
      expect(window.fetch).toHaveBeenCalledWith("foobar/1/pin/delete/1337", {
        method: "POST",
        headers: {
          Authorization: "Token foobar",
          "Content-Type": "application/json;charset=UTF-8",
        },
      });
    });

    it("calls checkStatus once", async () => {
      await apiService.deletePin("foobar", 1337);
      expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
    });

    it("returns the response code if successful", async () => {
      await expect(apiService.deletePin("foobar", 1337)).resolves.toEqual(200);
    });
  });
});

describe("getPinsForUser", () => {
  const payload = { ...pinProps };
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => payload,
      });
    });

    // Mock function for checkStatus
    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.getPinsForUser("jdaok", 25, 25);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/jdaok/pins?offset=25&count=25",
      {
        method: "GET",
      }
    );
  });

  it("returns the correct data objects", async () => {
    const result = await apiService.getPinsForUser("jdaok", 25, 25);
    expect(result).toEqual(payload);
  });

  it("throws appropriate error if username is missing", async () => {
    await expect(apiService.getPinsForUser("", 25, 25)).rejects.toThrow(
      SyntaxError("Username missing")
    );
  });

  it("calls checkStatus once", async () => {
    apiService.checkStatus = jest.fn();
    await apiService.getPinsForUser("jdaok", 25, 25);
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });
});

describe("submitReviewToCB", () => {
  const reviewToSubmit: CritiqueBrainzReview = {
    entity_name: "Shakira",
    entity_id: "bf24ca37-25f4-4e34-9aec-460b94364cfc",
    entity_type: "artist",
    text: "TEXT",
    languageCode: "en",
    rating: 4,
  };

  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({ id: "bf24ca37-25f4-4e34-9aec-460b94364cfc" }),
      });
    });

    // Mock function for checkStatus
    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.submitReviewToCB("fnord", "baz", reviewToSubmit);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/user/fnord/timeline-event/create/review",
      {
        method: "POST",
        headers: {
          Authorization: "Token baz",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({
          metadata: {
            entity_name: "Shakira",
            entity_id: "bf24ca37-25f4-4e34-9aec-460b94364cfc",
            entity_type: "artist",
            text: "TEXT",
            language: "en",
            rating: 4,
          },
        }),
      }
    );
  });

  it("calls checkStatus once", async () => {
    await apiService.submitReviewToCB("fnord", "shhh", reviewToSubmit);
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the id for the submitted review if successful", async () => {
    await expect(
      apiService.submitReviewToCB("fnord", "shhh", reviewToSubmit)
    ).resolves.toEqual({ id: "bf24ca37-25f4-4e34-9aec-460b94364cfc" });
  });
});

describe("deleteFeedEvent", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
      });
    });

    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.deleteFeedEvent(
      "recording_recommendation",
      "riksucks",
      "testToken",
      1337
    );
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/user/riksucks/feed/events/delete",
      {
        method: "POST",
        headers: {
          Authorization: "Token testToken",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({
          event_type: "recording_recommendation",
          id: 1337,
        }),
      }
    );
  });

  it("calls checkStatus once", async () => {
    await apiService.deleteFeedEvent(
      "recording_recommendation",
      "riksucks",
      "testToken",
      1337
    );
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("throws appropriate error if id is missing", async () => {
    await expect(
      apiService.deleteFeedEvent(
        "recording_recommendation",
        "riksucks",
        "testToken",
        (undefined as unknown) as number
      )
    ).rejects.toThrow(SyntaxError("Event ID not present"));
  });

  it("returns the response code if successful", async () => {
    await expect(
      apiService.deleteFeedEvent(
        "recording_recommendation",
        "riksucks",
        "testToken",
        1337
      )
    ).resolves.toEqual(200);
  });
});

describe("hideFeedEvent", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
      });
    });

    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.hideFeedEvent(
      "recording_recommendation",
      "riksucks",
      "testToken",
      1337
    );
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/user/riksucks/feed/events/hide",
      {
        method: "POST",
        headers: {
          Authorization: "Token testToken",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({
          event_type: "recording_recommendation",
          event_id: 1337,
        }),
      }
    );
  });

  it("calls checkStatus once", async () => {
    await apiService.hideFeedEvent(
      "recording_recommendation",
      "riksucks",
      "testToken",
      1337
    );
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("throws appropriate error if id is missing", async () => {
    await expect(
      apiService.hideFeedEvent(
        "recording_recommendation",
        "riksucks",
        "testToken",
        (undefined as unknown) as number
      )
    ).rejects.toThrow(SyntaxError("Event ID not present"));
  });

  it("returns the response code if successful", async () => {
    await expect(
      apiService.hideFeedEvent(
        "recording_recommendation",
        "riksucks",
        "testToken",
        1337
      )
    ).resolves.toEqual(200);
  });
});

describe("unhideFeedEvent", () => {
  beforeEach(() => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 200,
      });
    });

    apiService.checkStatus = jest.fn();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.unhideFeedEvent(
      "recording_recommendation",
      "riksucks",
      "testToken",
      1337
    );
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/user/riksucks/feed/events/unhide",
      {
        method: "POST",
        headers: {
          Authorization: "Token testToken",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({
          event_type: "recording_recommendation",
          event_id: 1337,
        }),
      }
    );
  });

  it("calls checkStatus once", async () => {
    await apiService.unhideFeedEvent(
      "recording_recommendation",
      "riksucks",
      "testToken",
      1337
    );
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("throws appropriate error if id is missing", async () => {
    await expect(
      apiService.unhideFeedEvent(
        "recording_recommendation",
        "riksucks",
        "testToken",
        (undefined as unknown) as number
      )
    ).rejects.toThrow(SyntaxError("Event ID not present"));
  });

  it("returns the response code if successful", async () => {
    await expect(
      apiService.unhideFeedEvent(
        "recording_recommendation",
        "riksucks",
        "testToken",
        1337
      )
    ).resolves.toEqual(200);
  });
});
