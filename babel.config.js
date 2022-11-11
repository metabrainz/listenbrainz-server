module.exports = {
  sourceType: "unambiguous",
  presets: [
    [
      "@babel/preset-typescript",
      {
        allowDeclareFields: true,
      },
    ],
    "@babel/preset-react",
    [
      "@babel/preset-env",
      {
        useBuiltIns: "usage",
        corejs: { version: "3.26", proposals: true },
        targets: {
          node: "12",
          browsers: ["> 0.2% and not dead", "firefox >= 44"],
        },
      },
    ],
  ],
  plugins: [
    [
      "@babel/plugin-transform-typescript",
      {
        allowDeclareFields: true,
      },
    ],
    "@babel/plugin-proposal-class-properties",
    "@babel/plugin-transform-runtime",
  ],
};
