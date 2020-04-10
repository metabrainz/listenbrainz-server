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

    // Mock function for setTimeout and console.warn
    jest.useFakeTimers();
  });

  it("calls fetch with correct parameters", async () => {
    await apiService.submitListens("foobar", "import", "foobar");
    expect(window.fetch).toHaveBeenCalledWith("foobar/1/submit-listens", {
      method: "POST",
      headers: {
        Authorization: "Token foobar",
        "Content-Type": "application/json;charset=UTF-8",
      },
      body: JSON.stringify({
        listen_type: "import",
        payload: "foobar",
      }),
    });
  });

  it("retries if submit fails", async () => {
    // Overide mock for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.reject();
    });

    await apiService.submitListens("foobar", "import", "foobar");
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

    await apiService.submitListens("foobar", "import", "foobar");
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

    await apiService.submitListens("foobar", "import", "foobar");
  });

  it("returns the response if successful", async () => {
    await expect(
      apiService.submitListens("foobar", "import", "foobar")
    ).resolves.toEqual({
      ok: true,
      status: 200,
    });
  });

  it("calls itself recursively if size of payload exceeds MAX_LISTEN_SIZE", async () => {
    // Change MAX_LISTEN_SIZE to 0
    apiService.MAX_LISTEN_SIZE = 9;

    const spy = jest.spyOn(apiService, "submitListens");
    await apiService.submitListens("foobar", "import", ["foo", "bar"]);
    expect(spy).toHaveBeenCalledTimes(3);
    expect(spy).toHaveBeenCalledWith("foobar", "import", ["foo", "bar"]);
    expect(spy).toHaveBeenCalledWith("foobar", "import", ["foo"]);
    expect(spy).toHaveBeenCalledWith("foobar", "import", ["bar"]);
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
