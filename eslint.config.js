/* eslint-disable @typescript-eslint/no-require-imports */
const { defineConfig } = require("eslint/config");

const globals = require("globals");

// const {
//     fixupConfigRules,
//     fixupPluginRules,
// } = require("@eslint/compat");

const tsParser = require("@typescript-eslint/parser");
const react = require("eslint-plugin-react");
const reactHooks = require("eslint-plugin-react-hooks");
const prettier = require("eslint-plugin-prettier");
const testingLibrary = require("eslint-plugin-testing-library");
const importPlugin = require("eslint-plugin-import");
const jest = require("eslint-plugin-jest");
const jsxA11y = require("eslint-plugin-jsx-a11y");
// const js = require("@eslint/js");
const tseslint = require("typescript-eslint");
const eslintPluginPrettierRecommended = require("eslint-plugin-prettier/recommended");

// const { FlatCompat } = require("@eslint/eslintrc");

// const compat = new FlatCompat({
//   baseDirectory: __dirname,
//   recommendedConfig: js.configs.recommended,
//   allConfig: js.configs.all,
// });

module.exports = defineConfig([
  tseslint.configs.recommended,
  eslintPluginPrettierRecommended,
  reactHooks.configs.flat.recommended,
  testingLibrary.configs["flat/react"],
  importPlugin.flatConfigs.typescript,
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        Atomics: "readonly",
        SharedArrayBuffer: "readonly",
      },

      parser: tsParser,
      ecmaVersion: 2018,
      sourceType: "module",

      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },

    // extends: fixupConfigRules(compat.extends(
    //     "plugin:react/recommended",
    //     "plugin:react-hooks/recommended",
    //     // "prettier/react",
    // )),

    plugins: {
      // react: fixupPluginRules(react),
      // "@typescript-eslint": typescriptEslint,
      prettier,
      react,
      "jsx-a11y": jsxA11y,
      // "testing-library": testingLibrary,
    },

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
        {
          exceptAfterSingleLine: true,
        },
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
  },
  {
    files: ["**/*.ts", "**/*.tsx"],

    rules: {
      "no-undef": "off",
      "no-use-before-define": "off",
      "@typescript-eslint/no-use-before-define": "warn",
      "react/require-default-props": "off",
      "no-shadow": "off",
      "@typescript-eslint/no-shadow": "error",
      "@typescript-eslint/no-unused-vars": "warn",
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-require-imports": "warn",
      "@typescript-eslint/ban-ts-comment": "warn",
    },
  },
  {
    files: ["**/*.test.js", "**/*.test.ts", "**/*.test.tsx"],

    languageOptions: {
      globals: {
        ...globals.jest,
      },
    },

    plugins: {
      jest,
      "testing-library": testingLibrary,
    },

    // extends: compat.extends("plugin:testing-library/react"),

    rules: {
      "import/no-extraneous-dependencies": "off",
      "jest/no-disabled-tests": "warn",
      "jest/no-focused-tests": "error",
      "jest/no-identical-title": "error",
      "jest/prefer-to-have-length": "warn",
      "jest/valid-expect": "error",
    },
  },
]);
