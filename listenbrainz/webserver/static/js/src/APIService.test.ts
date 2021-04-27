import APIService from "./APIService";

const apiService = new APIService("foobar");

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

  it("retries if submit fails", async () => {
    // Overide mock for fetch
    window.fetch = jest
      .fn()
      .mockImplementationOnce(() => {
        return Promise.reject(Error);
      })
      .mockImplementation(() => {
        return Promise.resolve({
          ok: true,
          status: 200,
        });
      });

    await apiService.submitListens("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);
    expect(setTimeout).toHaveBeenCalledTimes(1);
  });

  it("retries if error 429 is recieved fails", async () => {
    // Overide mock for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 429,
      });
    });

    await apiService.submitListens("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);
    expect(setTimeout).toHaveBeenCalledTimes(1);
  });

  it("skips if any other response code is recieved", async () => {
    // Overide mock for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        status: 404,
      });
    });

    await apiService.submitListens("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);
    expect(setTimeout).not.toHaveBeenCalled(); // no setTimeout calls for future retries
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
    expect(spy).toHaveBeenCalledWith("foobar", "import", [
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
    expect(spy).toHaveBeenCalledWith("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "foobar",
          track_name: "bazfoo",
        },
      },
    ]);
    expect(spy).toHaveBeenCalledWith("foobar", "import", [
      {
        listened_at: 1000,
        track_metadata: {
          artist_name: "bazfoo",
          track_name: "foobar",
        },
      },
    ]);
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
    await apiService.getLatestImport("ईशान");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/latest-import?user_name=%E0%A4%88%E0%A4%B6%E0%A4%BE%E0%A4%A8",
      {
        method: "GET",
      }
    );
  });

  it("calls checkStatus once", async () => {
    await apiService.getLatestImport("foobar");
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the latest import timestamp", async () => {
    await expect(apiService.getLatestImport("foobar")).resolves.toEqual(0);
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
    await apiService.setLatestImport("foobar", 0);
    expect(window.fetch).toHaveBeenCalledWith("foobar/1/latest-import", {
      method: "POST",
      headers: {
        Authorization: "Token foobar",
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({ ts: 0 }),
    });
  });

  it("calls checkStatus once", async () => {
    await apiService.setLatestImport("foobar", 0);
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the response code if successful", async () => {
    await expect(apiService.setLatestImport("foobar", 0)).resolves.toEqual(200);
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
    await apiService.submitFeedback("foobar", "foo", 1);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/feedback/recording-feedback",
      {
        method: "POST",
        headers: {
          Authorization: "Token foobar",
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify({ recording_msid: "foo", score: 1 }),
      }
    );
  });

  it("calls checkStatus once", async () => {
    await apiService.submitFeedback("foobar", "foo", 0);
    expect(apiService.checkStatus).toHaveBeenCalledTimes(1);
  });

  it("returns the response code if successful", async () => {
    await expect(
      apiService.submitFeedback("foobar", "foo", 0)
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
    await apiService.getFeedbackForUserForRecordings("foo", "bar,baz");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/feedback/user/foo/get-feedback-for-recordings?recordings=bar,baz"
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
