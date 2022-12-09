// When rendering the CBReviewModal component,
// There is a problem in the way our tests import the ReactTooltip library component
// that causes them to fail, mocking it allows them to pass.

const jest = require("jest-mock");

const mock = jest.fn().mockImplementation(() => {
  return "This is a mocked react-tooltip component.";
});

export default mock;
