// eslint-disable-next-line import/no-extraneous-dependencies
import "@testing-library/jest-dom";
import "whatwg-fetch";
import "./__mocks__/matchMedia";

// Mocking this custom hook because somehow rendering alert notifications in there is making Enzyme shit itself
// because Enzyme doesn't support React functional components
jest.mock("../src/hooks/useFeedbackMap");

// Mock localforage
jest.mock("localforage", () => ({
  createInstance: jest.fn(() => ({
    setItem: jest.fn(),
    getItem: jest.fn(),
    removeItem: jest.fn(),
    iterate: jest.fn(),
  })),
}));
