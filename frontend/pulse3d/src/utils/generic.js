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

export { deepCopy, hexToBase64, isArrayOfNumbers, loadCsvInputToArray, isArrayOfWellNames };
