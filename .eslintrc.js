module.exports = {
  env: {
    browser: true,
    es6: true,
  },
  extends: [
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "airbnb",
    "prettier",
    "prettier/@typescript-eslint",
    "prettier/react",
  ],
  globals: {
    Atomics: "readonly",
    SharedArrayBuffer: "readonly",
  },
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaFeatures: {
      jsx: true,
    },
    ecmaVersion: 2018,
    sourceType: "module",
  },
  plugins: ["react", "@typescript-eslint", "prettier", "testing-library"],
  rules: {
    "react/prop-types": "off",
    "react/jsx-filename-extension": "off",
    "react/jsx-props-no-spreading": "off",
    "react/no-did-update-set-state": "off",
    "import/extensions": "off",
    "no-unused-vars": "off",
    camelcase: "off",
    "prettier/prettier": "warn",
    "lines-between-class-members": [
      "error",
      "always",
      { exceptAfterSingleLine: true },
    ],
    "jsx-a11y/label-has-associated-control": [
      "error",
      {
        assert: "either",
      },
    ],
    "react/static-property-placement": "off",
    "class-methods-use-this": "off",
    "react/no-unused-class-component-methods": "off",
    "default-param-last": "off",
  },
  settings: {
    "import/resolver": {
      node: {
        extensions: [".js", ".jsx", ".ts", ".tsx"],
      },
    },
  },
  overrides: [
    {
      // Configuration specific to Typescript files.
      // These are defined mostly when the ESLint rules don't support typescript
      // Usually there is an equivalent typescript rule from typescript-eslint
      files: ["**/*.ts", "**/*.tsx"],
      rules: {
        // Disabling no-undef rule for typescript files
        // "The checks it provides are already provided by TypeScript without the need for configuration"
        // see https://typescript-eslint.io/docs/linting/troubleshooting/#i-get-errors-from-the-no-undef-rule-about-global-variables-not-being-defined-even-though-there-are-no-typescript-errors
        "no-undef": "off",
        // see https://typescript-eslint.io/rules/no-use-before-define/
        "no-use-before-define": "off",
        "@typescript-eslint/no-use-before-define": "warn",
        "react/require-default-props": "off",
        "no-shadow": "off",
        "@typescript-eslint/no-shadow": "error",
      },
    },
    {
      files: ["**/*.test.js", "**/*.test.ts", "**/*.test.tsx"],
      env: {
        jest: true,
      },
      plugins: ["jest"],
      extends: ["plugin:testing-library/react"],
      rules: {
        "import/no-extraneous-dependencies": "off",
        "jest/no-disabled-tests": "warn",
        "jest/no-focused-tests": "error",
        "jest/no-identical-title": "error",
        "jest/prefer-to-have-length": "warn",
        "jest/valid-expect": "error",
      },
    },
  ],
};
