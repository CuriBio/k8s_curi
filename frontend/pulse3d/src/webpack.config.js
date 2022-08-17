// This config is only intended for use by `npm build-sw`.
// Other scripts should use whatever webpack config is present in next.config.js

const path = require("path");

module.exports = {
  entry: {
    bundle: path.join(__dirname, "./serviceWorker.js"),
  },

  output: {
    filename: "serviceWorker.js",
    path: path.join(__dirname, "public"),
  },

  mode: process.env.NODE_ENV || "development",

  //   watchOptions: {
  //     ignored: /node_modules|dist|\.js/g,
  //   },

  //   resolve: {
  //     extensions: [".ts", ".tsx", ".js", ".json"],
  //     plugins: [],
  //   },

  //   module: {
  //     rules: [
  //       {
  //         test: /\.tsx?$/,
  //         loader: "awesome-typescript-loader",
  //       },
  //     ],
  //   },
};
