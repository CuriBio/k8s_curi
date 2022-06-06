import SparkMD5 from "spark-md5";

// Based on https://github.com/satazor/js-spark-md5#hash-a-file-incrementally

export default async function (file) {
  let blobSlice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice;
  let chunkSize = 2097152; // Read in chunks of 2MB
  let chunks = Math.ceil(file.size / chunkSize);
  let currentChunk = 0;
  let spark = new SparkMD5.ArrayBuffer();
  let fileReader = new FileReader();

  try {
    let fileHash = await new Promise((resolve, reject) => {
      fileReader.onload = function (e) {
        console.log("read chunk nr", currentChunk + 1, "of", chunks);
        spark.append(e.target.result); // Append array buffer
        currentChunk++;

        if (currentChunk < chunks) {
          loadNext();
        } else {
          resolve(spark.end());
        }
      };

      fileReader.onerror = function () {
        reject("oops, something went wrong.");
      };

      function loadNext() {
        let start = currentChunk * chunkSize;
        let end = start + chunkSize >= file.size ? file.size : start + chunkSize;

        fileReader.readAsArrayBuffer(blobSlice.call(file, start, end));
      }

      loadNext();
    });

    console.log("finished loading");
    console.log("computed hash", fileHash); // Compute hash

    return fileHash;
  } catch (e) {
    console.log(`Error occured while calculating md5 hash: ${e}`);
  }
}
