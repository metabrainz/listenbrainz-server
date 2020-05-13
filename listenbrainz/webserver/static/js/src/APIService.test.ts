import APIService from "./APIService";
import APIError from "./APIError";

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

describe("getUserStats", () => {
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
    await apiService.getUserStats("foobar", "all_time", 10, 5);
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/artists?offset=10&range=all_time&count=5"
    );
  });

  it("calls fetch correctly when optional parameters are not passed", async () => {
    await apiService.getUserStats("foobar");
    expect(window.fetch).toHaveBeenCalledWith(
      "foobar/1/stats/user/foobar/artists?offset=0&range=all_time"
    );
  });

  it("throws appropriate error if statistics haven't been calculated", async () => {
    window.fetch = jest.fn().mockImplementationOnce(() => {
      return Promise.resolve({
        ok: true,
        status: 204,
      });
    });

    await expect(apiService.getUserStats("foobar")).rejects.toThrow(
      Error("Statistics for the user haven't been calculated yet.")
    );
  });

  it("calls checkStatus once", async () => {
    apiService.checkStatus = jest.fn();

    await apiService.getUserStats("foobar");
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
