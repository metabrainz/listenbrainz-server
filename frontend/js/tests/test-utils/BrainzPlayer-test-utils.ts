
export const createBrainzPlayerSettings = (
  overrides: Partial<BrainzPlayerSettings> = {}
): BrainzPlayerSettings => ({
  brainzplayerEnabled: true,
  notificationsEnabled: true,
  spotifyEnabled: false,
  soundcloudEnabled: false,
  youtubeEnabled: false,
  appleMusicEnabled: false,
  internetArchiveEnabled: false,
  navidromeEnabled: false,
  funkwhaleEnabled: false,
  dataSourcesPriority: [],
  ...overrides,
});