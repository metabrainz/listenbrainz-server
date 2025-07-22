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
  setupFiles: ["jest-canvas-mock"],

  setupFilesAfterEnv: [
    "jest-location-mock",
    "<rootDir>/frontend/js/tests/jest-setup.ts",
  ],

  // The test environment that will be used for testing
  testEnvironment: "jest-fixed-jsdom",

  // The glob patterns Jest uses to detect test files
  testMatch: ["**/?(*.)+(spec|test).(ts|js)?(x)"],

  // An array of regexp pattern strings that are matched against all test paths, matched tests are skipped
  testPathIgnorePatterns: ["\\\\node_modules\\\\"],

  // This option sets the URL for the jsdom environment. It is reflected in properties such as location.href
  testEnvironmentOptions: {
    url: "http://localhost",
    customExportConditions: [""],
  },
  moduleNameMapper: {
    "react-markdown": "<rootDir>/frontend/js/tests/__mocks__/react-markdown.tsx",
    "^localforage$": "<rootDir>/frontend/js/tests/__mocks__/localforage.ts",
    "d3-interpolate":
      "<rootDir>/node_modules/d3-interpolate/dist/d3-interpolate.min.js",
    "d3-color": "<rootDir>/node_modules/d3-color/dist/d3-color.min.js",
    "d3-scale-chromatic":
      "<rootDir>/node_modules/d3-scale-chromatic/dist/d3-scale-chromatic.min.js",
    "d3-scale": "<rootDir>/node_modules/d3-scale/dist/d3-scale.min.js",
    "d3-shape": "<rootDir>/node_modules/d3-shape/dist/d3-shape.min.js",
    "d3-path": "<rootDir>/node_modules/d3-path/dist/d3-path.min.js",
  },
  transform: {
    "\\.[jt]sx?$": "ts-jest",
    "^.+\\.(js|jsx)$": "babel-jest",
  },

  // Indicates whether each individual test should be reported during the run
  verbose: true,

};
