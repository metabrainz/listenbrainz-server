// eslint-disable-next-line import/no-extraneous-dependencies
import "@testing-library/jest-dom";
import "./__mocks__/matchMedia";

// Mocking this custom hook because somehow rendering alert notifications in there is making Enzyme shit itself
// because Enzyme doesn't support React functional components
jest.mock("../src/hooks/useFeedbackMap");
