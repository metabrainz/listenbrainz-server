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
      userFeed: "/static/js/src/UserFeed.tsx",
      playlist: "/static/js/src/playlists/Playlist.tsx",
      playlists: "/static/js/src/playlists/Playlists.tsx",
      recommendations: "/static/js/src/recommendations/Recommendations.tsx",
    },
    output: {
      filename: isProd ? "[name].[contenthash].js" : "[name].js",
      path: "/static/js/dist",
    },
    devtool: isProd ? false : "inline-source-map",
    module: {
      rules: [
        {
          test: /\.(js|ts)x?$/,
          exclude: /node_modules/,
          use: {
            loader: "babel-loader",
            options: {
              presets: [
                [
                  "@babel/preset-env",
                  {
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
