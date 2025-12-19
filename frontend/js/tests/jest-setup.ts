// eslint-disable-next-line import/no-extraneous-dependencies
import "@testing-library/jest-dom";
import "./__mocks__/matchMedia";

// Mocking this custom hook because somehow rendering alert notifications in there is making Enzyme shit itself
// because Enzyme doesn't support React functional components
jest.mock("../src/hooks/useFeedbackMap");
// Mocking localforage globally to support iterate
jest.mock("localforage", () => {
  let store: Record<string, any> = {};

  return {
    createInstance: jest.fn(() => ({
      // Set Item
      setItem: jest.fn((key, value) => {
        store[key] = value;
        return Promise.resolve(value);
      }),
      // Get Item
      getItem: jest.fn((key) => {
        return Promise.resolve(store[key]);
      }),
      // Remove Item
      removeItem: jest.fn((key) => {
        delete store[key];
        return Promise.resolve();
      }),
      // Clear
      clear: jest.fn(() => {
        store = {};
        return Promise.resolve();
      }),
      // ✅ VITAL FIX: Iterate implementation for tests
      iterate: jest.fn(async (callback) => {
        const keys = Object.keys(store);
        for (let i = 0; i < keys.length; i++) {
          const key = keys[i];
          const value = store[key];
          // localforage callback signature: (value, key, iterationNumber)
          await callback(value, key, i);
        }
        return Promise.resolve();
      }),
    })),
  };
});
