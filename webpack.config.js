const path = require("path");
const { WebpackManifestPlugin } = require("webpack-manifest-plugin");
const { CleanWebpackPlugin } = require("clean-webpack-plugin");
const ForkTsCheckerWebpackPlugin = require("fork-ts-checker-webpack-plugin");

const baseDir = "/static";
const jsDir = path.join(baseDir, "js");
const distDir = path.join(baseDir, "dist");

module.exports = function (env) {
  const isProd = env === "production";
  const plugins = [
    new CleanWebpackPlugin(),
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
    mode: isProd ? "production" : "development",
    entry: {
      main: path.resolve(jsDir, "src/RecentListens.tsx"),
      recentListens: [
        path.resolve(jsDir, "src/RecentListens.tsx"),
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
    },
    devtool: isProd ? "source-map" : "eval-source-map",
    module: {
      rules: [
        {
          test: /\.(js|ts)x?$/,
          // some nivo/D3 dependencies need to be transpiled, we include them with the following regex
          exclude: /node_modules\/(?!(d3-array|d3-scale|internmap)\/).*/,
          // Don't specify the babel configuration here
          // Configuration can be found in ./babel.config.js
          use: "babel-loader",
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
