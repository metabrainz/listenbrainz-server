const path = require("path");
const { WebpackManifestPlugin } = require("webpack-manifest-plugin");
const ForkTsCheckerWebpackPlugin = require("fork-ts-checker-webpack-plugin");
const LessPluginCleanCSS = require("less-plugin-clean-css");

const baseDir = "/static";
const jsDir = path.join(baseDir, "js");
const distDir = path.join(baseDir, "dist");
const cssDir = path.join(baseDir, "css");

const es5LibrariesToTranspile = [
  "d3-array",
  "d3-scale",
  "internmap",
  "react-date-picker",
  "react-calendar",
  "socket.io-client",
  "socket.io-parser",
  "engine.io-client",
];
const babelExcludeLibrariesRegexp = new RegExp(
  `node_modules/(?!(${es5LibrariesToTranspile.join("|")})/).*`,
  ""
);
module.exports = function (env, argv) {
  const isProd = argv.mode === "production";
  const plugins = [
    new WebpackManifestPlugin(),
    new ForkTsCheckerWebpackPlugin({
      typescript: {
        diagnosticOptions: {
          semantic: true,
          syntactic: true,
        },
        mode: "write-references",
      },
      eslint: {
        // Starting the path with "**/" because of current dev/prod path discrepancy
        // In dev we bind-mount the source code to "/code/static" and in prod to "/static"
        // The "**/" allows us to ignore the folder structure and find source files in whatever CWD we're in.
        files: "**/js/src/**/*.{ts,tsx,js,jsx}",
        options: { fix: !isProd },
      },
    }),
  ];
  return {
    entry: {
      // Importing main.less file here so that it gets compiled.
      // Otherwise with a standalone entrypoint Webpack would generate a superfluous js file.
      // All the Less/CSS will be exported separately to a main.css file and not appear in the recentListens module
      recentListens: [
        path.resolve(jsDir, "src/RecentListens.tsx"),
        path.resolve(cssDir, "main.less"),
      ],
      import: path.resolve(jsDir, "src/LastFMImporter.tsx"),
      userEntityChart: path.resolve(jsDir, "src/stats/UserEntityChart.tsx"),
      userReports: path.resolve(jsDir, "src/stats/UserReports.tsx"),
      userPageHeading: path.resolve(jsDir, "src/UserPageHeading.tsx"),
      userFeed: path.resolve(jsDir, "src/user-feed/UserFeed.tsx"),
      playlist: path.resolve(jsDir, "src/playlists/Playlist.tsx"),
      playlists: path.resolve(jsDir, "src/playlists/Playlists.tsx"),
      recommendations: path.resolve(
        jsDir,
        "src/recommendations/Recommendations.tsx"
      ),
    },
    output: {
      filename: isProd ? "[name].[contenthash].js" : "[name].js",
      path: distDir,
      publicPath: `${distDir}/`,
      clean: true, // Clean the output directory before emit.
    },
    devtool: isProd ? "source-map" : "eval-source-map",
    module: {
      rules: [
        {
          test: /\.(js|ts)x?$/,
          // some third-party libraries need to be transpiled to ES5, we include them with the following regex
          exclude: babelExcludeLibrariesRegexp,
          // Don't specify the babel configuration here
          // Configuration can be found in ./babel.config.js
          use: "babel-loader",
        },
        {
          test: /\.less$/i,
          type: "asset/resource",
          loader: "less-loader",
          generator: {
            filename: isProd ? "[name].[contenthash].css" : "[name].css",
          },
          options: {
            lessOptions: {
              math: "always",
              plugins: [new LessPluginCleanCSS({ advanced: true })],
            },
          },
        },
      ],
    },
    resolve: {
      modules: ["/code/node_modules", path.resolve(baseDir, "node_modules")],
      extensions: [".ts", ".tsx", ".js", ".jsx", ".json"],
    },
    plugins,
  };
};
