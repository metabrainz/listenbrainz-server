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
          node: "16",
          browsers: ["> 0.2%", "last 2 versions", "not dead", "Firefox >= 44"],
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
