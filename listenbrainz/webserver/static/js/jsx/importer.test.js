import Importer from './importer'
import APIService from './api-service'

// Mock data to test functions
import encodeScrobble_input from './__mocks__/encodeScrobble_input.json'
// Output for the mock data
import encodeScrobble_output from './__mocks__/encodeScrobble_output.json'

jest.mock('./api-service');

const props = {
  user: {
    name: 'dummyUser',
    auth_token: 'foobar',
  },
  lastfmURL: 'foobar',
  lastfm_api_key: 'foobar',
}

describe('encodeScrobbles is working correctly', () => {
  beforeEach(() => {
    // Clear previous mocks
    APIService.mockClear();
  });

  it('encodes the given scrobbles correctly', () => {
    let importer = new Importer('dummyUser', props);
    expect(importer.encodeScrobbles(encodeScrobble_input)).toEqual(encodeScrobble_output);
  });
});
