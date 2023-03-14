const path = require("path");
const { WebpackManifestPlugin } = require("webpack-manifest-plugin");
const ForkTsCheckerWebpackPlugin = require("fork-ts-checker-webpack-plugin");
const LessPluginCleanCSS = require("less-plugin-clean-css");
const StylelintPlugin = require("stylelint-webpack-plugin");
const ESLintPlugin = require("eslint-webpack-plugin");

const es5LibrariesToTranspile = [
  "d3-array",
  "d3-scale",
  "internmap",
  "react-datetime-picker",
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
  const baseDir = "./frontend";
  const jsDir = path.join(baseDir, "js");
  const distDir = path.join(baseDir, "dist");
  const cssDir = path.join(baseDir, "css");
  const plugins = [
    new WebpackManifestPlugin(),
    new ForkTsCheckerWebpackPlugin({
      typescript: {
        diagnosticOptions: {
          semantic: true,
          syntactic: true,
        },
        mode: "write-references",
        memoryLimit: 4096,
      },
    }),
    new StylelintPlugin({
      configFile: ".stylelintrc.js",
      failOnError: isProd,
      files: "**/static/css/**/*.less",
      fix: !isProd,
      threads: true,
    }),
    new ESLintPlugin({
      files: path.join(jsDir, "src/**/*.{ts,tsx,js,jsx}"),
      fix: !isProd,
    }),
  ];
  return {
    entry: {
      // Importing main.less file here so that it gets compiled.
      // Otherwise with a standalone entrypoint Webpack would generate a superfluous js file.
      // All the Less/CSS will be exported separately to a main.css file and not appear in the recentListens module
      recentListens: [
        path.resolve(jsDir, "src/recent/RecentListens.tsx"),
        path.resolve(cssDir, "main.less"),
      ],
      listens: [path.resolve(jsDir, "src/user/Listens.tsx")],
      import: path.resolve(jsDir, "src/lastfm/LastFMImporter.tsx"),
      userEntityChart: path.resolve(jsDir, "src/stats/UserEntityChart.tsx"),
      userReports: path.resolve(jsDir, "src/stats/UserReports.tsx"),
      userPageHeading: path.resolve(jsDir, "src/user/UserPageHeading.tsx"),
      userTaste: path.resolve(jsDir, "src/user/UserTaste.tsx"),
      userFeed: path.resolve(jsDir, "src/user-feed/UserFeed.tsx"),
      playlist: path.resolve(jsDir, "src/playlists/Playlist.tsx"),
      playlists: path.resolve(jsDir, "src/playlists/Playlists.tsx"),
      explore: path.resolve(jsDir, "src/explore/ExploreCard.tsx"),
      huesound: path.resolve(jsDir, "src/explore/huesound/ColorPlay.tsx"),
      yearInMusic2021: path.resolve(
        jsDir,
        "src/explore/year-in-music/2021/YearInMusic.tsx"
      ),
      yearInMusic2022: path.resolve(
        jsDir,
        "src/explore/year-in-music/2022/YearInMusic.tsx"
      ),
      coverArtComposite: path.resolve(
        jsDir,
        "src/explore/year-in-music/2022/CoverArtComposite.tsx"
      ),
      homepage: path.resolve(jsDir, "src/home/Homepage.tsx"),
      recommendationsPlayground: path.resolve(
        jsDir,
        "src/recommendations/Recommendations.tsx"
      ),
      recommendations: path.resolve(
        jsDir,
        "src/recommendations/RecommendationsPage.tsx"
      ),
      missingMBData: path.resolve(
        jsDir,
        "src/missing-mb-data/MissingMBData.tsx"
      ),
      playerPage: path.resolve(jsDir, "src/player-pages/PlayerPage.tsx"),
      metadataViewer: path.resolve(
        jsDir,
        "src/metadata-viewer/MetadataViewerPageWrapper.tsx"
      ),
      freshReleases: path.resolve(
        jsDir,
        "src/explore/fresh-releases/FreshReleases.tsx"
      ),
      selectTimezone: path.resolve(
        jsDir,
        "src/user-settings/SelectTimezone.tsx"
      ),
      selectTroiPreferences: path.resolve(
        jsDir,
        "src/user-settings/SelectTroiPreferences.tsx"
      ),
    },
    output: {
      filename: isProd ? "[name].[contenthash].js" : "[name].js",
      path: path.resolve(distDir),
      // This is for the manifest file used by the server. Files end up in /static folder
      publicPath: `/static/dist/`,
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
      modules: [
        path.resolve("./node_modules"),
        "/code/node_modules",
        path.resolve(baseDir, "node_modules"),
      ],
      extensions: [".ts", ".tsx", ".js", ".jsx", ".json"],
    },
    plugins,
  };
};
