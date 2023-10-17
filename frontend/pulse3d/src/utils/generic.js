import * as apache from "apache-arrow";

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

const isArrayOfNumbers = (arr, positive = false) => {
  return arrayValidator(arr, () => {
    for (const n of arr) {
      if (typeof n !== "number" || (positive && n < 0)) {
        return false;
      }
    }
    return true;
  });
};

const isArrayOfWellNames = (arr) => {
  return arrayValidator(arr, () => {
    for (const n of arr) {
      if (typeof n !== "string" || n.length !== 2) {
        return false;
      }
      const row = n[0];
      const col = n[1];
      if (!"ABCD".includes(row) || !"123456".includes(col)) {
        return false;
      }
    }
    return true;
  });
};

const loadCsvInputToArray = (commaSeparatedInputs) => {
  // remove all whitespace before processing
  const strippedInput = commaSeparatedInputs.replace(/\s/g, "");
  const inputAsArrOfStrs = [...strippedInput.split(",")];
  return inputAsArrOfStrs;
};

const getPeaksValleysFromTable = async (table) => {
  const columns = table.schema.fields.map(({ name }) => name);
  //  columns are A1__peaks, A1__valleys, ....
  const wellNames = new Set(columns.map((name) => name.split("__")[0]));

  // filter out null values (0) and some values get randomly parsed to bigint values which cannot be converted to JSON
  const columnData = table.data[0].children.map(({ values }) => {
    return Array.from(values)
      .filter((idx) => idx !== 0)
      .map((val) => (typeof val === "bigint" ? parseInt(val) : val));
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

const getWaveformCoordsFromTable = async (table) => {
  const columns = table.schema.fields.map(({ name }) => name);
  const wellNames = columns.filter(
    (name) =>
      !name.includes("__raw") && !name.includes("__stim") && !name.includes("Time") && !name.includes("level")
  );
  const columnData = table.data[0].children.map(({ values }) => Array.from(values));
  // occassionally recordings end in a bunch of NaN/0 values if stim data is present so they need to be filtered out here
  // leaving time index aat 0 because it's meant to be 0
  const time = columnData[0].filter((val, i) => val !== 0 || (val === 0 && i === 0));

  const coordinatesObj = {};
  for (const well of wellNames) {
    // some analyses may only include a few xlsx files, not all wells
    const wellForceIdx = columns.indexOf(well);
    if (wellForceIdx !== -1) {
      let wellForce = columnData[wellForceIdx];

      const minForce = Math.min(...wellForce);
      wellForce = wellForce.map((val) => val - minForce);

      coordinatesObj[well] = time.map((time, i) => [time / 1e6, wellForce[i]]);
    }
  }

  return coordinatesObj;
};

const getTableFromParquet = async (buffer) => {
  const wasmModule = await import("parquet-wasm/esm/arrow1.js");
  await wasmModule.default();

  const parquetData = wasmModule.readParquet(buffer);
  return apache.tableFromIPC(parquetData);
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
};
