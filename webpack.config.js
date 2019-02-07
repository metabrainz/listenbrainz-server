const path = require('path');
const ManifestPlugin = require('webpack-manifest-plugin');
const CleanWebpackPlugin = require('clean-webpack-plugin');

module.exports = function(env){
  const isProd = env === "production";
  const plugins = [
    new CleanWebpackPlugin('/static/js/dist'),
    new ManifestPlugin()
  ];
  return {
    mode: isProd ? "production" : "development",
    entry: '/static/js/profile.jsx',
    output: {
      filename: isProd ? '[name].[contenthash].js' : '[name].js',
      path: '/static/js/dist'
    },
    module: {
      rules: [
        {
            test: [/\.js$/ , /\.jsx$/], exclude: /node_modules/, use: {
                loader: "babel-loader",
                options: {
                    "presets": [[
                          "@babel/preset-env",
                          {
                            "targets": {
                              "node": "10",
                              "browsers": [ "defaults" ]
                            }
                          }
                        ],
                        "@babel/preset-react"],
                    "plugins": ["@babel/plugin-proposal-class-properties"]
                }
            }
        }
      ]
    },
    resolve: {
        modules: ['/code/node_modules', '/static/node_modules']
    },
    plugins: plugins,
    watch: isProd ? true : false
}
};
