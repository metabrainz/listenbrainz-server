module.exports = {
  presets: [
    [
      "@babel/preset-env",
      {
        useBuiltIns: "usage",
        corejs: { version: "3.9", proposals: true },
        targets: {
          node: "10",
          browsers: ["> 0.2% and not dead", "firefox >= 44"],
        },
      },
    ],
    [
      "@babel/preset-typescript",
      {
        allowDeclareFields: true,
      },
    ],
    "@babel/preset-react",
  ],
  plugins: ["@babel/plugin-transform-runtime"],
};
