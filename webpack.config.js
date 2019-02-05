const path = require('path');
const ManifestPlugin = require('webpack-manifest-plugin');
const CleanWebpackPlugin = require('clean-webpack-plugin');

module.exports = function(env){
  const isProd = env === "production";
  const plugins = [
    new CleanWebpackPlugin(path.resolve(__dirname, 'listenbrainz/webserver/static/js/dist')),
    new ManifestPlugin()
  ];
  return {
    mode: isProd ? "production" : "development",
    entry: './listenbrainz/webserver/js/profile.jsx',
    output: {
      filename: isProd ? '[name].[contenthash].js' : '[name].js',
      path: path.resolve(__dirname, 'listenbrainz/webserver/static/js/dist')
    },
    module: {
      rules: [
        { test: [/\.js$/ , /\.jsx$/], exclude: /node_modules/, loader: "babel-loader" }
      ]
    },
    plugins: plugins,
    watch: isProd ? false : true
}
};