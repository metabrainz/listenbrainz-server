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
      AIBrainz: [path.resolve(jsDir, "src/explore/ai-brainz/AIBrainz.tsx")],
      dashboard: [path.resolve(jsDir, "src/user/Dashboard.tsx")],
      import: path.resolve(jsDir, "src/lastfm/LastFMImporter.tsx"),
      userEntityChart: path.resolve(
        jsDir,
        "src/user/charts/UserEntityChart.tsx"
      ),
      userReports: path.resolve(jsDir, "src/user/stats/UserReports.tsx"),
      userTaste: path.resolve(jsDir, "src/user/taste/UserTaste.tsx"),
      userFeed: path.resolve(jsDir, "src/user-feed/UserFeed.tsx"),
      playlist: path.resolve(jsDir, "src/playlists/Playlist.tsx"),
      playlists: path.resolve(jsDir, "src/user/playlists/Playlists.tsx"),
      explore: path.resolve(jsDir, "src/explore/Explore.tsx"),
      huesound: path.resolve(jsDir, "src/explore/huesound/ColorPlay.tsx"),
      lb_radio: path.resolve(jsDir, "src/explore/lb-radio/LBRadio.tsx"),
      yearInMusic2021: path.resolve(
        jsDir,
        "src/user/year-in-music/2021/YearInMusic2021.tsx"
      ),
      yearInMusic2022: path.resolve(
        jsDir,
        "src/user/year-in-music/2022/YearInMusic2022.tsx"
      ),
      yearInMusic2023: path.resolve(
        jsDir,
        "src/user/year-in-music/2023/YearInMusic2023.tsx"
      ),
      coverArtComposite2022: path.resolve(
        jsDir,
        "src/explore/cover-art-collage/2022/CoverArtComposite.tsx"
      ),
      coverArtComposite2023: path.resolve(
        jsDir,
        "src/explore/cover-art-collage/2023/CoverArtComposite.tsx"
      ),
      homepage: path.resolve(jsDir, "src/home/Homepage.tsx"),
      recommendationsPlayground: path.resolve(
        jsDir,
        "src/recommended/tracks/Recommendations.tsx"
      ),
      recommendations: path.resolve(
        jsDir,
        "src/user/recommendations/RecommendationsPage.tsx"
      ),
      playerPage: path.resolve(jsDir, "src/player/PlayerPage.tsx"),
      metadataViewer: path.resolve(
        jsDir,
        "src/metadata-viewer/MetadataViewerPage.tsx"
      ),
      freshReleases: path.resolve(
        jsDir,
        "src/explore/fresh-releases/FreshReleases.tsx"
      ),
      musicNeighborhood: path.resolve(
        jsDir,
        "src/explore/music-neighborhood/MusicNeighborhood.tsx"
      ),
      artCreator: path.resolve(jsDir, "src/explore/art-creator/ArtCreator.tsx"),
      artistPage: path.resolve(jsDir, "src/artist/ArtistPage.tsx"),
      albumPage: path.resolve(jsDir, "src/album/AlbumPage.tsx"),
      settingsPage: path.resolve(jsDir, "src/settings/index.tsx"),
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
        {
          // Supportthis library used by markdown-react, needs nodeJS style `process`
          test: /node_modules\/kleur\/index\.js/,
          use: [
            {
              loader: "imports-loader",
              options: {
                type: "commonjs",
                imports: ["single process/browser process", "kleur"],
              },
            },
          ],
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
