import { formatWSMessageToListen } from "./utils";

describe("formatWSMessageToListen", () => {
  const mockListen: Listen = {
    track_metadata: {
      artist_name: "Coldplay",
      track_name: "Viva La Vida",
      additional_info: {
        recording_msid: "2edee875-55c3-4dad-b3ea-e8741484f4b5",
      },
    },
    listened_at: 1586580524,
    listened_at_iso: "2020-04-10T10:12:04Z",
  };

  const mockWSListen = {
    data: {
      artist_name: "Coldplay",
      track_name: "Viva La Vida",
      additional_info: {},
    },
    recording_msid: "2edee875-55c3-4dad-b3ea-e8741484f4b5",
    timestamp: 1586580524,
    listened_at_iso: "2020-04-10T10:12:04Z",
  };
  it("renders a link if MBID is provided", () => {
    const result = formatWSMessageToListen(mockWSListen);
    expect(result).toEqual(mockListen);
  });
});
