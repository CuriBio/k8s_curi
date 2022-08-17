// Tanner (8/17/22): This config is only intended for use by `npm build-sw`.
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
};
