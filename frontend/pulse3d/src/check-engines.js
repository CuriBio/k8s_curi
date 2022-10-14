#!/usr/bin/env node

/*
  This module cannot contain any external libraries!

  Adapted from:
    - https://github.com/michalzaq12/electron-nuxt/blob/master/template/.electron-nuxt/check-engines.js
    - https://stackoverflow.com/questions/67831958/prevent-npm-start-if-node-version-mismatch
*/

const path = require("path");
const semver = require("semver");

const FG_RED = "\x1b[31m";
const RESET = "\x1b[0m";

const errorInRed = (msg) => {
  console.error(FG_RED + msg + RESET);
};

const packageDetails = (() => {
  const packagePath = path.join(process.cwd(), "./package.json");
  try {
    return require(packagePath);
  } catch (e) {
    errorInRed(`Could not find ${packagePath}`);
    process.exit(1);
  }
})();

const engines = packageDetails.engines;

if (!engines || !engines.node) {
  errorInRed("Please define 'engines.node' in package.json");
  process.exit(1);
}

const nodeVersionReq = engines.node;
const currentNodeVersion = semver.clean(process.version);

if (semver.satisfies(currentNodeVersion, nodeVersionReq)) {
  process.exit(0);
} else {
  errorInRed(`Invalid node version: ${currentNodeVersion} for requirement: ${nodeVersionReq}`);
  process.exit(1);
}
