import Importer from './importer'
import APIService from './api-service'

// Mock data to test functions
import page from './__mocks__/page.json'
import getInfo from './__mocks__/getInfo.json'
import getInfoNoPlayCount from './__mocks__/getInfoNoPlayCount.json'
// Output for the mock data
import encodeScrobble_output from './__mocks__/encodeScrobble_output.json'

jest.mock('./api-service');
jest.useFakeTimers();

const props = {
  user: {
    name: 'dummyUser',
    auth_token: 'foobar',
  },
  lastfm_api_url: 'http://ws.audioscrobbler.com/2.0/',
  lastfm_api_key: 'foobar',
};
const lastfmUsername = 'dummyUser';
const importer = new Importer(lastfmUsername, props);

describe('encodeScrobbles', () => {
  beforeEach(() => {
    // Clear previous mocks
    APIService.mockClear();
  });

  it('encodes the given scrobbles correctly', () => {
    expect(importer.encodeScrobbles(page)).toEqual(encodeScrobble_output);
  });
});

describe('getNumberOfPages', () => {
  beforeEach(() => {
    // Clear previous mocks
    APIService.mockClear();

    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(page),
      })
    })
  });

  it('should call with the correct url', () => {
    importer.getNumberOfPages();

    expect(window.fetch).toHaveBeenCalledWith(`${props.lastfm_api_url}?method=user.getrecenttracks&user=${lastfmUsername}&api_key=${props.lastfm_api_key}&from=1&format=json`);
  })

  it('should return number of pages', async () => {
    const num = await importer.getNumberOfPages();
    expect(num).toBe(1);
  })

  it('should return -1 if there is an error', async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
      })
    })

    const num = await importer.getNumberOfPages();
    expect(num).toBe(-1);
  })
})

describe('getTotalNumberOfScrobbles', () => {
  beforeEach(() => {
    // Clear previous mocks
    APIService.mockClear();

    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(getInfo),
      })
    })
  });

  it('should call with the correct url', () => {
    importer.getTotalNumberOfScrobbles();

    expect(window.fetch).toHaveBeenCalledWith(`${props.lastfm_api_url}?method=user.getinfo&user=${lastfmUsername}&api_key=${props.lastfm_api_key}&format=json`);
  })

  it('should return number of pages', async () => {
    const num = await importer.getTotalNumberOfScrobbles();
    expect(num).toBe(1026);
  })

  it('should return -1 if playcount is not available', async () => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(getInfoNoPlayCount),
      })
    })

    const num = await importer.getTotalNumberOfScrobbles();
    expect(num).toBe(-1);
  })

  it('should throw an error when fetch fails', async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
      })
    })
    await expect(importer.getTotalNumberOfScrobbles()).rejects.toThrowError();
  })
})

describe('getPage', () => {
  beforeEach(() => {
    // Clear previous mocks
    APIService.mockClear();

    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(page),
      })
    })
  });

  it('should call with the correct url', () => {
    importer.getPage(1);

    expect(window.fetch).toHaveBeenCalledWith(`${props.lastfm_api_url}?method=user.getrecenttracks&user=${lastfmUsername}&api_key=${props.lastfm_api_key}&from=1&page=1&format=json`);
  })

  it('should call encodeScrobbles', async () => {
    // Mock function for encodeScrobbles
    importer.encodeScrobbles = jest.fn(data => ["foo", "bar"]);

    const data = await importer.getPage(1);
    expect(importer.encodeScrobbles).toHaveBeenCalledTimes(1);
    expect(data).toEqual(["foo", "bar"]);
  })

  it('should retry if 50x error is recieved', async () => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 503,
      })
    })
    // Mock function for console.warn
    console.warn = jest.fn();

    await importer.getPage(1);
    // There is no direct way to check if retry has been called
    expect(setTimeout).toHaveBeenCalledTimes(1);
    expect(console.warn).toHaveBeenCalledWith('Got 503 fetching last.fm page=1, retrying in 3s')

    jest.runAllTimers();
  })

  it('should skip the page if 40x is recieved', async () => {
    // Mock function for failed fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: false,
        status: 404,
      })
    })

    // Mock function for console.warn
    console.warn = jest.fn();

    await importer.getPage(1);
    expect(console.warn).toHaveBeenCalledWith('Got 404, skipping')
  })

  it('should retry if there is any other error', async () => {
    // Mock function for fetch
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.reject(),
      })
    })
    // Mock function for console.warn
    console.warn = jest.fn();

    await importer.getPage(1);
    // There is no direct way to check if retry has been called
    expect(setTimeout).toHaveBeenCalledTimes(1);
    expect(console.warn).toHaveBeenCalledWith('Error fetching last.fm page=1, retrying in 3s')

    jest.runAllTimers();
  })
})

describe('submitPage', () => {
  beforeEach(() => {
    // Clear previous mocks
    APIService.mockClear();

    // Mock for getRateLimitDelay
    importer.updateRateLimitParameters = jest.fn();

    // Mock for console.warn
    console.warn = jest.fn();
  });

  it('calls submitListens once and increments numSuccesful', async () => {
    let spy = jest.spyOn(importer.APIService, 'submitListens').mockImplementation(async () => {
      return {"status": 200}
    });

    importer.submitPage();
    jest.runAllTimers();

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise(resolve => setImmediate(resolve));
    
    expect(importer.APIService.submitListens).toHaveBeenCalledTimes(1);
    expect(importer.APIService.submitListens).toHaveBeenCalledWith("foobar", "import", undefined);
    expect(importer.numSuccesful).toEqual(1);
  })

  it('retries if response "429" is recieved', async () => {
    let spy = jest.spyOn(importer.APIService, 'submitListens').mockImplementation(async () => {
      return {"status": 429}
    });

    importer.submitPage();
    jest.advanceTimersByTime(2999);

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise(resolve => setImmediate(resolve));

    expect(setTimeout).toHaveBeenCalledTimes(2);
  })

  it('skips when 4xx other than 429 is recieved', async () => {
    let spy = jest.spyOn(importer.APIService, 'submitListens').mockImplementation(async () => {
      return {"status": 404}
    });

    importer.submitPage();
    jest.runAllTimers();

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise(resolve => setImmediate(resolve));

    expect(console.warn).toHaveBeenCalledWith("4xx error, skipping");
  })

  it('skips when 5xx is recieved', async () => {
    let spy = jest.spyOn(importer.APIService, 'submitListens').mockImplementation(async () => {
      return {"status": 500}
    });

    importer.submitPage();
    jest.runAllTimers();

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise(resolve => setImmediate(resolve));

    expect(console.warn).toHaveBeenCalledWith("received http error 500 req'ing");
  })

  it('skips when anything else is recieved', async () => {
    let spy = jest.spyOn(importer.APIService, 'submitListens').mockImplementation(async () => {
      return {"status": 100}
    });

    importer.submitPage();
    jest.runAllTimers();

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise(resolve => setImmediate(resolve));

    expect(console.warn).toHaveBeenCalledWith("received http status 100, skipping");
  })

  it('retries when submitListens fails', async () => {
    let spy = jest.spyOn(importer.APIService, 'submitListens').mockImplementation(async () => {
      return Promise.reject();
    });

    importer.submitPage();
    jest.advanceTimersByTime(2999);

    // Flush all promises
    // https://stackoverflow.com/questions/51126786/jest-fake-timers-with-promises
    await new Promise(resolve => setImmediate(resolve));

    expect(console.warn).toHaveBeenCalledWith("Error, retrying in 3s");
    expect(setTimeout).toHaveBeenCalledTimes(2);
  })
})
