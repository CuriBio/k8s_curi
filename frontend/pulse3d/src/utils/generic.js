import * as apache from "apache-arrow";
import { capitalize } from "@mui/material";

const deepCopy = (obj) => {
  return JSON.parse(JSON.stringify(obj));
};

const hexToBase64 = (hexstring) => {
  return btoa(
    // TODO remove deprecated method btoa
    hexstring
      .match(/\w{2}/g)
      .map(function (a) {
        return String.fromCharCode(parseInt(a, 16));
      })
      .join("")
  );
};

const arrayValidator = (arr, validator_fn) => {
  return Array.isArray(arr) && validator_fn(arr);
};

const isInt = (value) => {
  return Number.isInteger(Number(value));
};

const isArrayOfNumbers = (arr, positive = false, allowFloat = true, additionalCheck = () => true) => {
  return arrayValidator(arr, () => {
    for (const n of arr) {
      if (typeof n !== "number" || (positive && n < 0) || (!allowFloat && !isInt(n)) || !additionalCheck(n)) {
        return false;
      }
    }
    return true;
  });
};

const isArrayOfWellNames = (arr) => {
  return arrayValidator(arr, () => {
    for (const n of arr) {
      if (!isValidWellName(n)) {
        return false;
      }
    }
    return true;
  });
};

const isValidWellName = (name) => {
  // Tanner (4/10/24): this does not support 1536 well plates and will need to be updated when support for them is required
  if (typeof name !== "string" || name.length < 2) {
    return false;
  }
  const match = name.match(/^[A-P](?<col>\d{1,2})$/);
  if (match) {
    const col = parseInt(match.groups.col);
    return 1 <= col && col <= 24;
  }
  return false;
};

const loadCsvInputToArray = (commaSeparatedInputs) => {
  // remove all whitespace before processing
  const strippedInput = commaSeparatedInputs.replace(/\s/g, "");
  const inputAsArrOfStrs = [...strippedInput.split(",")];
  return inputAsArrOfStrs;
};

const getPeaksValleysFromTable = async (table) => {
  const columns = table.schema.fields.map(({ name }) => name);

  const parseFn = columns.includes("time") ? _getPeaksValleysFromTable : _getPeaksValleysFromLegacyTable;
  const peaksValleyObj = parseFn(table, columns);

  return peaksValleyObj;
};

const _getPeaksValleysFromTable = (table, columns) => {
  // for current format of tables, columns are time, <well>
  const wellNames = new Set(columns.filter((col) => col != "time"));

  // convert bigint values which cannot be converted to JSON
  const columnData = table.data[0].children.map(({ values }) => {
    return Array.from(values).map((val) => (typeof val === "bigint" ? parseInt(val) : val));
  });

  const peaksValleysObj = {};
  for (const well of wellNames) {
    const columnIdx = columns.indexOf(well);
    if (columnIdx === -1) continue;

    const peakIdxs = [];
    const valleyIdxs = [];
    columnData[columnIdx].map((featureMarker, idx) => {
      if (featureMarker === 1) {
        peakIdxs.push(idx);
      } else if (featureMarker === 2) {
        valleyIdxs.push(idx);
      }
    });

    peaksValleysObj[well] = [peakIdxs, valleyIdxs];
  }

  return peaksValleysObj;
};

const _getPeaksValleysFromLegacyTable = (table, columns) => {
  // for legacy format of tables, columns are <well>__peaks, <well>__valleys
  const wellNames = new Set(columns.map((name) => name.split("__")[0]));

  // filter out null values (0) and some values get randomly parsed to bigint values which cannot be converted to JSON
  const columnData = table.data[0].children.map(({ values }) => {
    const res = Array.from(values)
      .filter((idx) => idx !== 0 && idx !== 0n)
      .map((val) => (typeof val === "bigint" ? parseInt(val) : val));
    return res;
  });

  const peaksValleysObj = {};
  for (const well of wellNames) {
    if (columns.indexOf(`${well}__peaks`) !== -1) {
      // assign each well [[...peaks], [...valleys]]
      const [peaksIdx, valleysIdx] = ["peaks", "valleys"].map((type) => columns.indexOf(`${well}__${type}`));
      peaksValleysObj[well] = [columnData[peaksIdx], columnData[valleysIdx]];
    }
  }

  return peaksValleysObj;
};

const getWaveformCoordsFromTable = async (table, normalizationMethod, productPage) => {
  const columns = table.schema.fields.map(({ name }) => name);
  const wellNames = columns.filter(
    (name) =>
      !name.includes("__raw") &&
      !name.includes("__stim") &&
      !name.includes("Time") &&
      !name.includes("level") &&
      name !== "time"
  );
  const columnData = table.data[0].children.map(({ values }) => Array.from(values));
  // occassionally recordings end in a bunch of NaN/0 values if stim data is present so they need to be filtered out here
  // leaving time index at 0 because it's meant to be 0
  const time = columnData[0].filter((val, i) => val !== 0 || (val === 0 && i === 0));

  if (productPage.toLowerCase().includes("mantarray") && !normalizationMethod) {
    normalizationMethod = "F-Fmin";
  }

  const convertTimeUnits = !columns.includes("time");

  const coordinatesObj = {};
  for (const well of wellNames) {
    // some analyses may only include a few xlsx files, not all wells
    const wellForceIdx = columns.indexOf(well);
    if (wellForceIdx !== -1) {
      const wellForce = _normalize(columnData[wellForceIdx], normalizationMethod);
      coordinatesObj[well] = time.map((time, i) => [convertTimeUnits ? time / 1e6 : time, wellForce[i]]);
    }
  }

  return coordinatesObj;
};

const _normalize = (wellForce, normMethod) => {
  const minForce = Math.min(...wellForce);

  let normFn;
  if (normMethod === "F-Fmin") {
    normFn = (val) => val - minForce;
  } else if (normMethod === "F/Fmin") {
    normFn = (val) => val / minForce;
  } else if (normMethod === "∆F/Fmin") {
    normFn = (val) => (val - minForce) / minForce;
  } else {
    // no normalization
    return wellForce;
  }

  return wellForce.map(normFn);
};

const getTableFromParquet = async (buffer) => {
  const wasmModule = await import("parquet-wasm/esm/arrow1.js");
  await wasmModule.default();

  const parquetData = wasmModule.readParquet(buffer);
  return apache.tableFromIPC(parquetData);
};

const formatDateTime = (datetime, includeSeconds) => {
  if (datetime) {
    const format = {
      hour: "numeric",
      minute: "numeric",
    };
    if (includeSeconds) {
      format.second = "numeric";
    }
    return new Date(datetime + "Z").toLocaleDateString(undefined, format);
  } else {
    const now = new Date();
    const datetime =
      now.getFullYear() +
      "-" +
      (now.getMonth() + 1) +
      "-" +
      now.getDate() +
      "-" +
      now.getHours() +
      now.getMinutes() +
      now.getSeconds();
    return datetime;
  }
};

const applyWindow = (data, xMin, xMax) => {
  const halfWindowedData = data.filter((coords) => coords[0] <= xMax);
  const windowEndIdx = halfWindowedData.length - 1;
  const dataWithinWindow = halfWindowedData.filter((coords) => coords[0] >= xMin);
  const windowStartIdx = halfWindowedData.length - dataWithinWindow.length;
  return { dataWithinWindow, windowStartIdx, windowEndIdx };
};

const getMinP3dVersionForProduct = (productType) => {
  switch (productType) {
    case "nautilai":
      return "0.34.4";
    default:
      return "0.0.0";
  }
};

const formatP3dJob = (job, selectedJobs, accountId) => {
  try {
    const { id, upload_id, created_at, object_key, status, meta, user_id } = job;
    const analyzedFile = object_key?.split("/").slice(-1) || "";
    const isChecked = Object.keys(selectedJobs).includes(id);
    const parsedMeta = (typeof meta === "string" ? JSON.parse(meta) : meta) || {};
    // Tanner (4/30/24): if jobs are missing analysis params for some reason, need to set to an empty object otherwise errors will occur
    const analysisParams = parsedMeta.analysis_params || {};
    // add pulse3d version used on job to be displayed with other analysis params
    if ("version" in parsedMeta) {
      analysisParams.pulse3d_version = parsedMeta.version;
    }
    const metaParams = { analysisParams };

    if ("name_override" in parsedMeta) {
      metaParams.nameOverride = parsedMeta.name_override;
    }

    if ("error_msg" in parsedMeta) {
      status += `: ${parsedMeta.error_msg}`;
    }

    const owner = accountId === user_id.replace(/-/g, "");

    return {
      jobId: id,
      uploadId: upload_id,
      analyzedFile,
      createdAt: created_at,
      status,
      checked: isChecked,
      owner,
      ...metaParams,
    };
  } catch (e) {
    console.log(`ERROR formatting pulse3d job ${job?.id}`, e);
    return null;
  }
};

const formatAdvancedAnalysisJob = (job) => {
  try {
    const { id, name, type: jobType, sources, created_at: createdAt, meta, status } = job;
    let parsedMeta = {};
    try {
      parsedMeta = JSON.parse(meta);
    } catch {}

    const filename = name || parsedMeta.output_name || "None";

    return {
      id,
      filename,
      jobType,
      createdAt,
      sources,
      meta: parsedMeta,
      status,
    };
  } catch (e) {
    console.log(`ERROR formatting advanced analysis job ${job?.id}`, e);
    return null;
  }
};

const formatNotificationMessage = (msg) => {
  const { id, created_at, viewed_at, subject, body } = msg;

  return {
    id,
    createdAt: created_at,
    viewed: !!viewed_at,
    subject,
    body,
  };
};

const getSortedWellListStr = (wells) => {
  try {
    return wells.sort().join(", ");
  } catch {
    return wells;
  }
};

const compareStr = (s1, s2) => {
  s1 = s1.toLowerCase();
  s2 = s2.toLowerCase();
  if (s1 < s2) {
    return -1;
  }
  if (s1 > s2) {
    return 1;
  }
  return 0;
};

const productTitle = (s) => {
  return s
    .split("_")
    .map((s) => capitalize(s))
    .join(" ");
};

const getLocalTzOffsetHours = () => {
  try {
    return Math.floor(new Date().getTimezoneOffset() / -60);
  } catch {
    return 0;
  }
};

export {
  deepCopy,
  hexToBase64,
  isArrayOfNumbers,
  loadCsvInputToArray,
  isArrayOfWellNames,
  getPeaksValleysFromTable,
  getWaveformCoordsFromTable,
  getTableFromParquet,
  formatDateTime,
  applyWindow,
  isInt,
  getMinP3dVersionForProduct,
  formatP3dJob,
  formatAdvancedAnalysisJob,
  formatNotificationMessage,
  productTitle,
  compareStr,
  getLocalTzOffsetHours,
  getSortedWellListStr,
};
