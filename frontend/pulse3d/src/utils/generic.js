import { WellTitle as LabwareDefinition } from "@/utils/labwareCalculations";
const twentyFourPlateDefinition = new LabwareDefinition(4, 6);
const wellNames = Array(24)
  .fill()
  .map((_, idx) => twentyFourPlateDefinition.getWellNameFromIndex(idx));

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
  const columnData = table.data[0].children.map(({ values }) =>
    Array.from(values)
      .filter((idx) => idx !== 0)
      .map((val) => (typeof val === "bigint" ? parseInt(val) : val))
  );

  const peaksValleysObj = {};

  for (const well of wellNames) {
    const [peaksIdx, valleysIdx] = ["peaks", "valleys"].map((type) => columns.indexOf(`${well}__${type}`));
    peaksValleysObj[well] = [columnData[peaksIdx], columnData[valleysIdx]];
  }

  return peaksValleysObj;
};

const getWaveformCoordsFromTable = async (table, normalizeYAxis) => {
  const columns = table.schema.fields.map(({ name }) => name);
  // 0s are null in the table
  const columnData = table.data[0].children.map(({ values }) => Array.from(values));
  const time = columnData[0];
  const coordinatesObj = {};

  for (const well of wellNames) {
    const wellForceIdx = columns.indexOf(well);
    let wellForce = columnData[wellForceIdx];

    if (normalizeYAxis) {
      const minForce = Math.min(...wellForce);
      wellForce = wellForce.map((val) => val - minForce);
    }

    coordinatesObj[well] = time.map((time, i) => [time / 1e6, wellForce[i]]);
  }

  return coordinatesObj;
};

export {
  getPeaksValleysFromTable,
  getWaveformCoordsFromTable,
  hexToBase64,
  isArrayOfNumbers,
  loadCsvInputToArray,
  isArrayOfWellNames,
};
