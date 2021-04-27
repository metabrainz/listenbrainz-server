const path = require("path");
const ManifestPlugin = require("webpack-manifest-plugin");
const { CleanWebpackPlugin } = require("clean-webpack-plugin");
const ForkTsCheckerWebpackPlugin = require("fork-ts-checker-webpack-plugin");

module.exports = function (env) {
  const isProd = env === "production";
  const plugins = [
    new CleanWebpackPlugin(),
    new ManifestPlugin(),
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
      main: "/static/js/src/RecentListens.tsx",
      import: "/static/js/src/LastFMImporter.tsx",
      userEntityChart: "/static/js/src/stats/UserEntityChart.tsx",
      userReports: "/static/js/src/stats/UserReports.tsx",
      userPageHeading: "/static/js/src/UserPageHeading.tsx",
      userFeed: "/static/js/src/user-feed/UserFeed.tsx",
      playlist: "/static/js/src/playlists/Playlist.tsx",
      playlists: "/static/js/src/playlists/Playlists.tsx",
      recommendations: "/static/js/src/recommendations/Recommendations.tsx",
    },
    output: {
      filename: isProd ? "[name].[contenthash].js" : "[name].js",
      path: "/static/js/dist",
    },
    devtool: isProd ? "source-map" : "eval-source-map",
    module: {
      rules: [
        {
          test: /\.(js|ts)x?$/,
          // some nivo/D3 dependencies need to be transpiled, we include them with the following regex
          exclude: /node_modules\/(?!(d3-array|d3-scale|internmap)\/).*/,
          use: {
            loader: "babel-loader",
            options: {
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
                "@babel/preset-typescript",
                "@babel/preset-react",
              ],
              plugins: [
                "@babel/plugin-proposal-class-properties",
                "@babel/plugin-transform-runtime",
              ],
            },
          },
        },
      ],
    },
    resolve: {
      modules: ["/code/node_modules", "/static/node_modules"],
      extensions: [".ts", ".tsx", ".js", ".jsx", ".json"],
    },
    plugins,
    watch: !isProd,
  };
};
