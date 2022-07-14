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

const isArrayOfNumbers = (arr, positive = false) => {
  if (!Array.isArray(arr)) {
    return false;
  }
  for (const n of arr) {
    if (typeof n !== "number" || (positive && n < 0)) {
      return false;
    }
  }
  return true;
};

export { hexToBase64, isArrayOfNumbers };
