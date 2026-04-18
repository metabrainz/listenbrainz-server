
export const createBrainzPlayerSettings = (
  overrides: Partial<BrainzPlayerSettings> = {}
): BrainzPlayerSettings => ({
  brainzplayerEnabled: true,
  spotifyEnabled: false,
  soundcloudEnabled: false,
  youtubeEnabled: false,
  appleMusicEnabled: false,
  internetArchiveEnabled: false,
  navidromeEnabled: false,
  funkwhaleEnabled: false,
  tidalEnabled: false,
  dataSourcesPriority: [],
  ...overrides,
});