import Importer from './importer'
import APIService from './api-service'

// Mock data to test functions
import page from './__mocks__/page.json'
import getInfo from './__mocks__/getInfo.json'
import getInfoNoPlayCount from './__mocks__/getInfoNoPlayCount.json'
// Output for the mock data
import encodeScrobble_output from './__mocks__/encodeScrobble_output.json'

jest.mock('./api-service');

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

describe('encodeScrobbles is working correctly', () => {
  beforeEach(() => {
    // Clear previous mocks
    APIService.mockClear();
  });

  it('encodes the given scrobbles correctly', () => {
    expect(importer.encodeScrobbles(page)).toEqual(encodeScrobble_output);
  });
});

describe('getNumberOfPages works correctly', () => {
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
        ok: failed,
      })
    })

    const num = await importer.getNumberOfPages();
    expect(num).toBe(-1);
  })
})

describe('getTotalNumberOfScrobbles works correctly', () => {
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
    // Mock function for failed fetch
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
        ok: failed,
      })
    })
    await expect(importer.getTotalNumberOfScrobbles()).rejects.toThrowError();
  })
})
