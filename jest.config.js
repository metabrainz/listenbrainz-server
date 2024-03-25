// For a detailed explanation regarding each configuration property, visit:
// https://jestjs.io/docs/en/configuration.html

module.exports = {
  preset: "ts-jest",

  // Automatically clear mock calls and instances between every test
  clearMocks: true,

  // An array of glob patterns indicating a set of files for which coverage information should be collected
  collectCoverageFrom: ["<rootDir>/frontend/js/**/*.{ts,tsx,js,jsx}"],

  // The directory where Jest should output its coverage files
  coverageDirectory: "coverage",

  // An array of file extensions your modules use
  moduleFileExtensions: ["ts", "tsx", "js", "json", "jsx"],

  // The paths to modules that run some code to configure or set up the testing environment before each test
  setupFiles: ["<rootDir>/enzyme.config.ts", "jest-canvas-mock"],

  setupFilesAfterEnv: [
    "jest-location-mock",
    "<rootDir>/frontend/js/tests/jest-setup.ts",
  ],

  // The test environment that will be used for testing
  testEnvironment: "jest-environment-jsdom",

  // The glob patterns Jest uses to detect test files
  testMatch: ["**/?(*.)+(spec|test).(ts|js)?(x)"],

  // An array of regexp pattern strings that are matched against all test paths, matched tests are skipped
  testPathIgnorePatterns: ["\\\\node_modules\\\\"],

  // This option sets the URL for the jsdom environment. It is reflected in properties such as location.href
  testEnvironmentOptions: {
    url: "http://localhost",
  },
  moduleNameMapper: {
    'react-markdown': '<rootDir>/node_modules/react-markdown/react-markdown.min.js',
  },
  transform: {
    "\\.[jt]sx?$": "ts-jest",
    "^.+\\.(js|jsx)$": "babel-jest"
  },

  // An array of regexp pattern strings that are matched against all source file paths, matched files will skip transformation
  // Re-include d3 packages
  transformIgnorePatterns: [
    "<rootDir>/node_modules/(?!(d3-color|d3-scale-chromatic))",
  ],

  // Indicates whether each individual test should be reported during the run
  verbose: true,

  snapshotSerializers: ["enzyme-to-json/serializer"],

  snapshotFormat: {
    escapeString: true,
    printBasicPrototype: true,
  },
};
