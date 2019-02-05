const path = require('path');

module.exports = function(env){
  const isProd = env === "production";
  return {
    mode: isProd ? "production" : "development",
    entry: './listenbrainz/webserver/js/profile.jsx',
    output: {
      filename: 'main.js',
      path: path.resolve(__dirname, 'listenbrainz/webserver/static/js/dist')
    },
    module: {
      rules: [
        { test: [/\.js$/ , /\.jsx$/], exclude: /node_modules/, loader: "babel-loader" }
      ]
    },
    watch: isProd ? false : true
}
};