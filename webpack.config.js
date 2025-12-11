const path = require("path");
const { WebpackManifestPlugin } = require("webpack-manifest-plugin");
const ForkTsCheckerWebpackPlugin = require("fork-ts-checker-webpack-plugin");
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
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
  "",
);
module.exports = function (env, argv) {
  const isProd = argv.mode === "production";
  const baseDir = "./frontend";
  const jsDir = path.join(baseDir, "js");
  const distDir = path.join(baseDir, "dist");
  const cssDir = path.join(baseDir, "css");
  const sassDir = path.join(cssDir, "sass");
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
      files: "**/static/css/**/*.{less,scss}",
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
      // Importing main sass entrypoint file here so that it gets compiled.
      // Otherwise with a standalone entrypoint Webpack would generate a superfluous js file.
      // All the Sass/CSS will be exported separately to a main.css/vendor.css files and not appear in the index module
      indexPage: [
        path.resolve(jsDir, "src/index.tsx"),
        path.resolve(sassDir, "main.scss"),
        path.resolve(sassDir, "vendors.scss"),
      ],
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
          test: /\.scss$/i,
          type: "asset/resource",
          loader: "sass-loader",
          generator: {
            filename: isProd ? "[name].[contenthash].css" : "[name].css",
          },
        },
        {
          test: /\.css$/i,
          use: ["style-loader", "css-loader"],
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
    optimization: {
      minimize: isProd,
      minimizer: [new CssMinimizerPlugin()],
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
