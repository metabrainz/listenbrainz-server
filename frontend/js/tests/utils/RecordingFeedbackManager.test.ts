import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";
import APIService from "../../src/utils/APIService";

describe("RecordingFeedbackManager", () => {
  let manager: RecordingFeedbackManager;
  let apiService: APIService;
  let mockUser: ListenBrainzUser;

  beforeEach(() => {
    apiService = new APIService("http://localhost");
    mockUser = {
      name: "testuser",
      auth_token: "token123",
    } as ListenBrainzUser;
    manager = new RecordingFeedbackManager(apiService, mockUser);
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  describe("fetchFeedback with retry mechanism", () => {
    it("successfully fetches feedback on first try", async () => {
      const mockResponse = {
        feedback: [
          { recording_mbid: "mbid1", score: 1 },
          { recording_msid: "msid1", score: -1 },
        ],
      };
      
      apiService.getFeedbackForUserForRecordings = jest
        .fn()
        .mockResolvedValue(mockResponse);

      manager.mbidFetchQueue.push("mbid1");
      manager.msidFetchQueue.push("msid1");

      await manager.fetchFeedback();

      expect(apiService.getFeedbackForUserForRecordings).toHaveBeenCalledTimes(1);
      expect(manager.recordingMBIDFeedbackMap.get("mbid1")).toBe(1);
      expect(manager.recordingMSIDFeedbackMap.get("msid1")).toBe(-1);
      expect(manager.mbidFetchQueue).toHaveLength(0);
      expect(manager.msidFetchQueue).toHaveLength(0);
    });

    it("retries on network error and succeeds", async () => {
      const mockResponse = {
        feedback: [{ recording_mbid: "mbid1", score: 1 }],
      };

      apiService.getFeedbackForUserForRecordings = jest
        .fn()
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce(mockResponse);

      manager.mbidFetchQueue.push("mbid1");

      const fetchPromise = manager.fetchFeedback();
      
      // fast-forward through the retry delay (1s)
      await jest.advanceTimersByTimeAsync(1500);

      await fetchPromise;

      expect(apiService.getFeedbackForUserForRecordings).toHaveBeenCalledTimes(2);
      expect(manager.recordingMBIDFeedbackMap.get("mbid1")).toBe(1);
    });

    it("fails after max retries and logs error", async () => {
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation();

      apiService.getFeedbackForUserForRecordings = jest
        .fn()
        .mockRejectedValue(new Error("Persistent error"));

      manager.mbidFetchQueue.push("mbid1");

      const fetchPromise = manager.fetchFeedback();
      
      // fast-forward through all retry delays (1s + 2s + 4s = 7s)
      await jest.advanceTimersByTimeAsync(8000);

      await fetchPromise;

      expect(apiService.getFeedbackForUserForRecordings).toHaveBeenCalledTimes(4); // initial + 3 retries
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to fetch recording feedback after retries:",
        expect.any(Error)
      );
      
      consoleErrorSpy.mockRestore();
    });

    it("uses exponential backoff for retries", async () => {
      const mockResponse = {
        feedback: [{ recording_mbid: "mbid1", score: 1 }],
      };

      apiService.getFeedbackForUserForRecordings = jest
        .fn()
        .mockRejectedValueOnce(new Error("Error 1"))
        .mockRejectedValueOnce(new Error("Error 2"))
        .mockResolvedValueOnce(mockResponse);

      manager.mbidFetchQueue.push("mbid1");

      const fetchPromise = manager.fetchFeedback();

      // first retry after 1s
      await jest.advanceTimersByTimeAsync(1000);
      expect(apiService.getFeedbackForUserForRecordings).toHaveBeenCalledTimes(2);

      // Second retry after additional 2s
      await jest.advanceTimersByTimeAsync(2000);
      expect(apiService.getFeedbackForUserForRecordings).toHaveBeenCalledTimes(3);

      await fetchPromise;
    });
  });
});