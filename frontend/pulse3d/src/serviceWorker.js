// Tanner (8/17/22): moved this file out of public/ since it is now processed by webpack
// which will place the compiled output file into public/ instead. This uncompiled file does not
// need to be included in any build steps, just the compiled webpack output

import jwtDecode from "jwt-decode";
import { Mutex } from "async-mutex";
const AdmZip = require("adm-zip");
const arrayBufferToBuffer = require("arraybuffer-to-buffer");

/* Global state of SW */
const refreshMutex = new Mutex();

let ClientSource = null;
let reloadNeeded = false;

const cacheName = "swCache";
const dbName = "swDB";
const storeName = "userInfo";
let db;

const MANTARRAY_URL = new URLSearchParams(location.search).get("mantarray_url");
const USERS_URL = new URLSearchParams(location.search).get("users_url");
const PULSE3D_URL = new URLSearchParams(location.search).get("pulse3d_url");
const USAGE_URLS = ["/login", "/uploads", "/jobs"];

// add timestamps to logging
const originalLog = console.log;

console.log = function () {
  const time = new Date().toLocaleTimeString("en-US", {
    hour12: false,
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
  });
  originalLog(...[`[SW @ ${time}]`, ...arguments]);
};

let logoutTimer = null;

const deleteUserDatabase = () => {
  const deletionReq = indexedDB.deleteDatabase(dbName);

  deletionReq.onsuccess = function () {
    console.log("Deleted database successfully");
  };
  deletionReq.onerror = function () {
    console.log("Couldn't delete database");
  };
  deletionReq.onblocked = function () {
    console.log("Couldn't delete database due to the operation being blocked");
  };
};

const clearAccountInfo = async () => {
  await caches.delete(cacheName);
  deleteUserDatabase();
  clearTimeout(logoutTimer);

  // TODO change all console.log to console.debug and figure out how to enable debug logging
  console.log("account info cleared");
};

const tokensExpiredLogout = () => {
  console.log("Sending logout ping because tokens expired");
  sendLogoutMsg();
};

const sendLogoutMsg = () => {
  clearAccountInfo();
  ClientSource.postMessage({ msgType: "logout" });
  console.log("logout ping sent");
};

const isRequest = (url, pathname) => {
  return url.pathname.includes(pathname);
};

/* SETTERS */

const setItem = async (key, item) => {
  const objectStore = db.transaction(storeName, "readwrite").objectStore(storeName);
  const updateRequest = objectStore.put({ id: key, value: item });

  updateRequest.onerror = (e) => console.log(`Error updating record for ${key}: ${e.target.errorCode}`);
  // need to close transaction/db connection otherwise db deletion on logout is blocked
  db.close();
};

const getItem = async (key) => {
  // returning a promise to get the value inside onsuccess handler
  return new Promise((resolve, reject) => {
    const objectStore = db.transaction(storeName, "readonly").objectStore(storeName);
    const getRequest = objectStore.get(key);

    getRequest.onsuccess = () => resolve(getRequest.result ? getRequest.result.value : null);
    // TODO could handle this error better, even if item doesn't exist, onsuccess gets called
    getRequest.onerror = (e) => {
      console.log(`Error getting record for ${key}: ${e.target.errorCode}`);
      reject();
    };

    // need to close transaction/db connection otherwise db deletion on logout is blocked
    db.close();
  });
};

const openDB = async (callback, key, value) => {
  return new Promise((resolve, reject) => {
    // ask to open the db
    const openRequest = indexedDB.open(dbName);

    openRequest.onerror = function (event) {
      console.log("Error opening indexedDB: " + event.target.errorCode);
      reject();
    };

    // upgrade needed is called when there is a new version of you db schema that has been defined
    openRequest.onupgradeneeded = function (event) {
      db = event.target.result;

      if (!db.objectStoreNames.contains(storeName)) {
        // if there's no store of 'storeName' create a new object store
        db.createObjectStore(storeName, { keyPath: "id" });
      }

      console.log("Successfully upgraded database and added object store");
    };

    openRequest.onsuccess = async function (event) {
      db = event.target.result;
      let res = callback ? await callback(key, value) : null;
      resolve(res);
    };
  });
};

const setTokens = async (tokens) => {
  await openDB(setItem, "tokens", tokens);

  // clear old logout timer if one already exists
  if (logoutTimer) {
    clearTimeout(logoutTimer);
  }

  // set up new logout timer
  const expTime = new Date(jwtDecode(tokens.refresh.token).exp * 1000);
  const currentTime = new Date().getTime();
  const millisBeforeLogOut = expTime - currentTime;

  logoutTimer = setTimeout(tokensExpiredLogout, millisBeforeLogOut);
};

/* GETTERS */
const getAuthTokens = async () => {
  const tokens = { access: null, refresh: null };

  if (db) {
    const storedTokens = await openDB(getItem, "tokens");

    if (storedTokens) {
      tokens.access = storedTokens.access.token;
      tokens.refresh = storedTokens.refresh.token;
    }
  }

  return tokens;
};

const getValueFromToken = async (name) => {
  const storedTokens = await getAuthTokens();

  if (!storedTokens.access) {
    return null;
  }

  let value = jwtDecode(storedTokens.access)[name];

  return value;
};

/* Request intercept functions */
const modifyRequest = async (req, url) => {
  // setup new headers
  const headers = new Headers({
    ...req.headers,
    "Content-Type": "application/json",
  });

  const storedTokens = await getAuthTokens();
  if (!isRequest(url, "/login") && storedTokens.access !== null) {
    // login request does not require the Authorization header,
    // and if there are no tokens that should mean that no account is logged in
    // and the request should fail with 403
    headers.append("Authorization", `Bearer ${storedTokens.access}`);
  }

  // apply new headers. Make sure to clone the original request obj if consuming the body by calling json()
  // since it typically can only be consumed once
  const modifiedReq = new Request(url, {
    headers,
    body: !["GET", "DELETE"].includes(req.method) ? JSON.stringify(await req.clone().json()) : null,
    method: req.method,
    credentials: "include", // required to send cookie
  });

  return modifiedReq;
};

const handleRefreshRequest = async () => {
  console.log("Requesting new tokens in handleRefreshRequest");
  let res = null;

  try {
    const storedTokens = await getAuthTokens();

    res = await fetch(`${USERS_URL}/refresh`, {
      method: "POST",
      body: JSON.stringify({}),
      headers: { Authorization: `Bearer ${storedTokens.refresh}` },
      credentials: "include", // required to send cookie
    });
  } catch (e) {
    console.log("ERROR in refresh req:", e.message);
    return { error: JSON.stringify(e.message) };
  }

  // set new tokens if refresh was successful
  // tokens should get cleared later if refresh failed
  if (res.status === 201) {
    const newTokens = await res.json();
    await setTokens(newTokens);
  }

  return res.status;
};

const requestWithRefresh = async (req, url) => {
  const safeRequest = async () => {
    const modifiedReq = await modifyRequest(req, url);
    try {
      return await fetch(modifiedReq);
    } catch (e) {
      return JSON.stringify(e.message);
    }
  };

  let response = await safeRequest();

  if (response.status === 401) {
    // guard with mutex so multiple requests do not try to refresh simultaneously
    const retryRequest = await refreshMutex.runExclusive(async () => {
      // check remaining lifetime of access token
      const nowNoMillis = Math.floor(Date.now() / 1000);
      const accessTokenExp = await getValueFromToken("exp");
      if (accessTokenExp - nowNoMillis < 10) {
        // refresh tokens since the access token less than 10 seconds away from expiring
        const refreshResponseStatus = await handleRefreshRequest();
        // only retry the original request if the refresh succeeds
        return refreshResponseStatus === 201;
      }
      // since access token is not close to expiring, assume refresh was just triggered by a
      // different request and try this request again
      return true;
    });
    if (retryRequest) {
      response = await safeRequest();
    }
  }

  return response;
};

const interceptResponse = async (req, url) => {
  if (isRequest(url, "/login")) {
    const modifiedReq = await modifyRequest(req, url);
    const response = await fetch(modifiedReq);
    let data = await response.json();

    if (response.status === 200) {
      const usage = data.error && data.error === "UsageError" ? data.message : data.usage_quota;
      // these three need to remain independent cache items even though they use the same response because they get updated from different requests later
      // sending usage at login, is separate from auth check request because it's not needed as often
      // set tokens if login was successful
      await setTokens(data.tokens);
      await openDB(setItem, "usage", usage);
      await openDB(setItem, "userScopes", data.user_scopes);
      await openDB(setItem, "adminScopes", data.admin_scopes);

      // remove tokens after
      data = {};
    }

    // send the response without the tokens so they are always contained within this service worker
    return new Response(JSON.stringify(data), {
      headers: response.headers,
      status: response.status,
      statusText: response.statusText,
    });
  } else {
    const response = await requestWithRefresh(req, url);
    const responseClone = response.clone();
    // these URLs will return usage_error in the body with a 200 response
    if (USAGE_URLS.includes(url.pathname) && req.method === "POST" && response.status == 200) {
      const data = await responseClone.json();
      const usage = data.error && data.error === "UsageError" ? data.message : data.usage_quota;
      await openDB(setItem, "usage", usage);
    } else if (isRequest(url, "/preferences") && response.status == 200) {
      const data = await responseClone.json();
      await openDB(setItem, "preferences", data);
    } else if (isRequest(url, "/logout")) {
      // just clear account info if user purposefully logs out
      clearAccountInfo();
    } else if (response.status === 401 || response.status === 403) {
      // if any other request receives an unauthorized or forbidden error code, send logout ping (this fn will also clear account info)
      console.log(`Sending logout ping because ${response.status} was returned from ${url.pathname}`);
      sendLogoutMsg();
    }

    return response;
  }
};

const convertLargeArrToJson = (arr) => {
  return "[" + arr.map((el) => JSON.stringify(el)).join(",") + "]";
};

const getWaveformDataFromS3 = async (res) => {
  let data = {};

  let response;
  try {
    response = await res.json();
  } catch (e) {
    console.log("Error getting response JSON: " + e);
    return data;
  }

  data.amplitudeLabel = response.amplitude_label;

  let timeForceRes;
  try {
    timeForceRes = await fetch(response.time_force_url);
  } catch (e) {
    console.log("Error retrieving waveform data: " + e);
    return data;
  }

  try {
    const timeForceBuf = response.time_force_url.includes(".zip")
      ? await _unzip(timeForceRes)
      : await timeForceRes.arrayBuffer();

    data.timeForceData = convertLargeArrToJson(new Uint8Array(timeForceBuf));
  } catch (e) {
    console.log("Error processing waveform data: " + e);
    return data;
  }

  let peaksValleysRes;
  try {
    peaksValleysRes = await fetch(response.peaks_valleys_url);
  } catch (e) {
    console.log("Error retrieving peaks/valleys: " + e);
    return data;
  }

  try {
    data.peaksValleysData = convertLargeArrToJson(new Uint8Array(await peaksValleysRes.arrayBuffer()));
  } catch (e) {
    console.log("Error processing peaks/valleys: " + e);
    return data;
  }

  return data;
};

const _unzip = async (res) => {
  const zip = new AdmZip(arrayBufferToBuffer(await res.arrayBuffer()));
  const buf = zip.readFile("tissue_waveforms.parquet");
  return buf;
};

/* Event listeners of SW */

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
  console.log("Service worker installed!");
  reloadNeeded = true;
});

self.addEventListener("activate", (event) => {
  // delete any previous cache from previous sessions
  event.waitUntil(
    caches
      .keys()
      .then(function (cacheNames) {
        return Promise.all(
          cacheNames.map(function (cacheName) {
            console.log("Deleting cache for: ", cacheName);
            return caches.delete(cacheName);
          })
        );
      })
      .then(() => deleteUserDatabase())
  );
  console.log("Service worker ready!");
});
// Intercept all fetch requests
self.addEventListener("fetch", async (e) => {
  let destURL = new URL(e.request.url);

  if (
    (e.request.url.includes(USERS_URL) ||
      e.request.url.includes(PULSE3D_URL) ||
      e.request.url.includes(MANTARRAY_URL)) &&
    !isRequest(destURL, "/email") && // this request doesn't depend on a token
    !isRequest(destURL, "/account") // we don't need to intercept verify request because it's handling own token
  ) {
    // only intercept requests to pulse3d, user and mantarray APIs
    e.respondWith(
      caches.open(cacheName).then(async (cache) => {
        // Go to the cache first
        const cachedResponse = await cache.match(e.request.url);
        // For now, only return cached responses for waveform data requests
        if (cachedResponse && isRequest(destURL, "/waveform-data")) {
          console.log(`Returning cached response for ${destURL}`);
          return cachedResponse;
        }
        // Otherwise, hit the network
        let response = await interceptResponse(e.request, destURL);

        // before returning response, check if you need to preload other wells
        // this needs to go after interceptResponse so that the initial A1 data gets returned first and not blocked by other requests
        if (isRequest(destURL, "/waveform-data")) {
          const fetchedData = await getWaveformDataFromS3(response);
          response = new Response(JSON.stringify(fetchedData), {
            status: response.status,
            statusText: response.statusText,
          });
          // only store if successful request
          if (response && response.status === 200) cache.put(e.request, response.clone());
        }

        return response;
      })
    );
  } else {
    e.respondWith(fetch(e.request));
  }
});

self.onmessage = async ({ data, source }) => {
  ClientSource = source;

  const { msgType, routerPathname } = data;
  const baseMsg = { msgType, routerPathname };
  let msgInfo = {};

  if (msgType === "checkReloadNeeded") {
    msgInfo = { reloadNeeded };
    reloadNeeded = false;
  } else if (msgType === "authCheck") {
    console.log("Returning authentication check");
    const storedTokens = await getAuthTokens();
    const accountType = await getValueFromToken("account_type");
    const accountId = await getValueFromToken(accountType === "user" ? "userid" : "customer_id");

    msgInfo = {
      isLoggedIn:
        storedTokens.access !== null && Date.now() < new Date((await getValueFromToken("exp")) * 1000),
      accountInfo: {
        accountType,
        accountId,
        accountScope: await getValueFromToken("scopes"),
      },
      usageQuota: await openDB(getItem, "usage"),
      userScopes: await openDB(getItem, "userScopes"),
      adminScopes: await openDB(getItem, "adminScopes"),
      preferences: (await openDB(getItem, "preferences")) || {},
    };
  } else if (msgType === "stayAlive") {
    // TODO should have this do something else so that there isn't a log msg produced every 20 seconds
    console.log("Staying alive");
  } else if (msgType === "clearData") {
    // a way for the FE components to force clear all stored data in the service worker
    console.log("Received clear message type to clear account info");
    clearAccountInfo();
  }

  if (Object.keys(msgInfo).length > 0) {
    source.postMessage({
      ...baseMsg,
      ...msgInfo,
    });
  }
};

export const accessToInternalsForTesting = {
  tokens: await getAuthTokens(),
  logoutTimer,
  ClientSource,
  accountType: await getValueFromToken("account_type"),
};
