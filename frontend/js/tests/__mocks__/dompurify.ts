// DOMPurify works fine in the code, but throws an error in tests
// (Cannot read properties of undefined (reading 'sanitize'))
// Mocking the component since it's only purpose is to sanitize inputs, which we don't test

const jest = require("jest-mock");

const DOMPurifyMock = {
  sanitize: jest.fn().mockImplementation((input: string) => input),
};

export default DOMPurifyMock;
