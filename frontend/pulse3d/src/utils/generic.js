const hexToBase64 = (hexstring) => {
  return btoa(
    // TODO remove deprecated method btoa
    hexstring
      .match(/\w{2}/g)
      .map(function (a) {
        return String.fromCharCode(parseInt(a, 16));
      })
      .join(""),
  );
};

export default hexToBase64;
