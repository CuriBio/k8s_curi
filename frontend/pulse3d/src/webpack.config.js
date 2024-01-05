// Tanner (8/17/22): This config is only intended for use by `npm build-sw`.
// Other scripts should use whatever webpack config is present in next.config.js

const path = require("path");
const webpack = require("webpack");

const mode = process.env.NODE_ENV || "development";
console.log(`Building service worker in ${mode} mode\n`);

module.exports = {
  resolve: {
    extensions: [".ts", ".js"],
    fallback: {
      crypto: false,
      fs: false,
      path: false,
      zlib: false,
      buffer: require.resolve("buffer"),
    },
  },
  entry: {
    bundle: path.join(__dirname, "./serviceWorker.js"),
  },
  output: {
    filename: "serviceWorker.js",
    path: path.join(__dirname, "public"),
  },
  mode,
  experiments: {
    topLevelAwait: true,
  },
  plugins: [
    new webpack.ProvidePlugin({
      Buffer: ["buffer", "Buffer"],
    }),
  ],
};
