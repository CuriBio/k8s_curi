import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import AnalysisParamForm from "@/components/uploadForm/AnalysisParamForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import FileDragDrop from "@/components/uploadForm/FileDragDrop";
import SparkMD5 from "spark-md5";
import { hexToBase64, getMinP3dVersionForProduct } from "@/utils/generic";
import { useRouter } from "next/router";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import semverGte from "semver/functions/gte";
import InputDropdownWidget from "@/components/basicWidgets/InputDropdownWidget";
import { AuthContext, UploadsContext } from "@/pages/_app";
import { parseS3XmlErrorCode } from "@/utils/generic";

const Container = styled.div`
  justify-content: center;
  position: relative;
  padding: 3rem;
`;

const Header = styled.h2`
  position: relative;
  text-align: center;
  background-color: var(--dark-blue);
  color: var(--light-gray);
  margin: auto;
  width: 100%;
  height: 75px;
  line-height: 3;
`;

const UploadCreditUsageInfo = styled.div`
  color: red;
  width: 57%;
  margin: auto;
  text-align: center;
  border: 3px solid red;
  padding: 1rem;
  margin-top: 2rem;
  margin-bottom: 0;
`;

const Uploads = styled.div`
  width: 100%;
  min-width: 1200px;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 15px;
  background-color: white;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: 3rem 8rem;
  width: 100%;
`;

const SuccessText = styled.span`
  color: green;
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
  line-height: 3;
`;

const DropDownContainer = styled.div`
  width: 100%;
  display: flex;
  justify-content: center;
  position: relative;
  height: 17%;
  align-items: center;
  margin-top: 20px;
`;

const RemoveButton = styled.button`
  border: none;
  background-color: var(--dark-grey);
  font-style: italic;

  &:hover {
    color: var(--teal-green);
    text-decoration: underline;
    cursor: pointer;
  }
`;

const dropZoneText = "CLICK HERE or DROP";
const defaultUploadErrorLabel =
  "Something went wrong while attempting to start the analysis for the following file(s):";
const defaultBadFilesLabel =
  "The following file(s) cannot be uploaded due to being an invalid file type, or a zip with an incorrect number of files.";

const modalObj = {
  uploadsReachedDuringSession: {
    header: "Warning!",
    messages: [
      "The upload limit has been reached for this customer account during your session preventing this recording from being uploaded.",
      "You will only be allowed to perform re-analysis on existing files.",
    ],
  },
  jobsReachedDuringSession: {
    header: "Warning!",
    messages: [
      "All usage limits have been reached for this customer account during your session preventing this analyses from starting.",
      "You will not be able to upload new recording files or perform re-analysis on existing files.",
    ],
  },
  jobsReachedAfterAnalysis: {
    header: "Warning!",
    messages: [
      "All usage limits have now been reached for this customer account.",
      "You will not be able to upload new recording files or perform re-analysis on existing files.",
    ],
  },
};

const MAX_WHOLE_UPLOAD_SIZE = 50 * 1024 * 1024;
const MULTIPART_UPLOAD_CHUNK_SIZE = 30 * 1024 * 1024;

const isReanalysisPage = (router) => {
  return (
    typeof router.query.id === "string" && router.query.id.toLowerCase() === "re-analyze existing upload"
  );
};

const checkWindowsErrors = (windowsErrors) => {
  return windowsErrors.some(({ start, end }) => {
    return start !== "" || end !== "";
  });
};

const fileMd5sChunks = async (file) => {
  let totalHasher = new SparkMD5.ArrayBuffer();
  let chunkHashes = [];

  let start = 0;
  while (start < file.size) {
    let end = Math.min(file.size, start + MULTIPART_UPLOAD_CHUNK_SIZE);
    let chunk = await file.slice(start, end).arrayBuffer();
    totalHasher.append(chunk);
    chunkHashes.push(hexToBase64(SparkMD5.ArrayBuffer.hash(chunk)));
    start = end;
  }

  let totalHash = hexToBase64(totalHasher.end());

  return [totalHash, chunkHashes];
};

export default function UploadForm() {
  const { usageQuota, preferences, productPage } = useContext(AuthContext);

  const { uploads, pulse3dVersions, defaultUploadForReanalysis } = useContext(UploadsContext);

  const getDefaultPulse3dVersion = () => {
    const defaultVersion = preferences?.[productPage]?.version || pulse3dVersions[0];
    return defaultVersion || "";
  };

  const getDefaultAnalysisParams = () => {
    return {
      normalizeYAxis: "",
      baseToPeak: "",
      peakToBase: "",
      maxY: "",
      twitchWidths: "",
      windows: [],
      stiffnessFactor: null,
      selectedPulse3dVersion: getDefaultPulse3dVersion(), // Tanner (9/15/22): The pulse3d version technically isn't a param, but it lives in the same part of the form as the params
      wellsWithFlippedWaveforms: "",
      showStimSheet: "",
      platemapName: "",
      wellGroups: {},
      stimWaveformFormat: "",
      nameOverride: "",
      // nautilai params
      normalizationMethod: productPage === "nautilai" ? "∆F/Fmin" : null,
      dataType: null,
      detrend: null,
      // width coord params
      relaxationSearchLimit: "",
      // original peak finding params
      prominenceFactorPeaks: "",
      prominenceFactorValleys: "",
      widthFactorPeaks: "",
      widthFactorValleys: "",
      // noise based peak finding params
      relativeProminenceFactor: "",
      noiseProminenceFactor: "",
      minPeakWidth: "",
      maxPeakWidth: "",
      minPeakHeight: "",
      maxPeakFreq: "",
      valleySearchDuration: "",
      upslopeDuration: "",
      upslopeNoiseAllowance: "",
      // NMJ
      nmjSingleAxisSensing: null,
      // CLS
      highFidelityMagnetProcessing: null,
    };
  };

  const router = useRouter();

  const [files, setFiles] = useState(defaultUploadForReanalysis || []);
  const [formattedUploads, setFormattedUploads] = useState([]);
  const [isButtonDisabled, setIsButtonDisabled] = useState(true);
  const [paramErrors, setParamErrors] = useState({});
  const [inProgress, setInProgress] = useState(false);
  const [modalButtons, setModalButtons] = useState(["Close"]);
  const [failedUploadsMsg, setFailedUploadsMsg] = useState([defaultUploadErrorLabel]);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [checkedParams, setCheckedParams] = useState(false);
  const [modalState, setModalState] = useState(false);
  const [usageModalState, setUsageModalState] = useState(false);
  const [usageModalLabels, setUsageModalLabels] = useState(modalObj.uploadsReachedDuringSession);
  const [analysisParams, setAnalysisParams] = useState(getDefaultAnalysisParams());
  const [badFiles, setBadFiles] = useState([]);
  const [resetDragDrop, setResetDragDrop] = useState(false);
  const [windowsErrors, setWindowsErrors] = useState([]);
  const [wellGroupErr, setWellGroupErr] = useState(false);
  const [reanalysis, setReanalysis] = useState(isReanalysisPage(router));
  const [minPulse3dVersionForCurrentUploads, setMinPulse3dVersionForCurrentUploads] = useState(
    getMinP3dVersionForProduct(productPage)
  );
  const [analysisPresetName, setAnalysisPresetName] = useState();
  const [userPresets, setUserPresets] = useState([]);
  const [selectedPresetIdx, setSelectedPresetIdx] = useState();
  const [savePresetChecked, setSavePresetChecked] = useState(false);

  useEffect(() => {
    if (badFiles.length > 0) {
      // give users the option to proceed with clean files if any, otherwise just close
      setModalButtons(["Close"]);
      // add files to modal to notify user which files are bad
      setFailedUploadsMsg([defaultBadFilesLabel, ...badFiles.map((f) => f.name)]);
      setModalState(true);
    }
  }, [badFiles]);

  useEffect(() => {
    const checkValidSelection = () => {
      if (files.length === 0) {
        return false;
      } else if (reanalysis) {
        return uploads && uploads.some((upload) => upload.id === files[0].id);
      } else {
        return files[0] instanceof File;
      }
    };

    // checks if error value exists, no file is selected, or upload is in progress
    const checkConditions =
      !Object.values(paramErrors).every((val) => val.length === 0) ||
      !checkValidSelection() ||
      inProgress ||
      wellGroupErr ||
      checkWindowsErrors(windowsErrors);

    setIsButtonDisabled(checkConditions);
  }, [paramErrors, files, inProgress, wellGroupErr, windowsErrors]);

  useEffect(() => {
    populateFormWithPresetParams();
  }, [selectedPresetIdx]);

  useEffect(() => {
    // resets upload status when user makes changes
    if (files.length > 0 || checkedParams) {
      setUploadSuccess(false);
    }
  }, [files, checkedParams]);

  useEffect(() => {
    // check for incorrect files and let user know
    checkFileContents();
  }, [files]);

  useEffect(() => {
    if (productPage && preferences) {
      setAnalysisParams(getDefaultAnalysisParams());
    }
  }, [productPage, preferences]);

  useEffect(() => {
    if (productPage) {
      setMinPulse3dVersionForCurrentUploads(getMinP3dVersionForProduct(productPage));
      getAnalysisPresets();
    }
  }, [productPage]);

  useEffect(() => {
    const newAnalysisStatus = isReanalysisPage(router);
    // only perform these updates if the page actually changed
    if (reanalysis !== newAnalysisStatus) {
      setReanalysis(newAnalysisStatus);
      // reset all params if the user switches between the "re-analyze" and "new upload" versions of this page
      resetState();
    }
  }, [router.query]);

  useEffect(() => {
    if (uploads) {
      setFormattedUploads([...uploads.map((upload) => upload.filename).filter((name) => name)]);
    }
  }, [uploads]);

  const populateFormWithPresetParams = () => {
    // start with default parameters
    // checking against null or undefined because index 0 won't pass otherwise
    if (Number.isInteger(selectedPresetIdx)) {
      const currentParams = getDefaultAnalysisParams();
      const presetParams = JSON.parse(userPresets[selectedPresetIdx].parameters);

      for (const param in presetParams) {
        // older presets may have a name override set, if so we want to ignore it
        if (param === "nameOverride") {
          continue;
        }
        const windowNameMapping = { startTime: "start", endTime: "end" };
        if (windowNameMapping[param] != null) {
          const paramValue = presetParams[param];
          if (paramValue != null && paramValue !== "") {
            if (currentParams.windows.length === 0) {
              currentParams.windows.push({ start: "", end: "" });
            }
            currentParams.windows[0][windowNameMapping[param]] = paramValue;
          }
        }

        // checking that the param exists in case params change over time, do not directly replace assuming all values match
        // and don't update if already default value
        if (param in currentParams && presetParams[param] !== currentParams[param]) {
          currentParams[param] = presetParams[param];
          // protect against deprecated pulse3d versions
          if (param === "selectedPulse3dVersion" && !pulse3dVersions.includes(presetParams[param])) {
            currentParams[param] = pulse3dVersions[0];
          }
        }
      }

      setAnalysisParams(currentParams);
      // also clear error messages
      setParamErrors({});
      setWindowsErrors([]);
    }
  };

  const getAnalysisPresets = async () => {
    if (!productPage) {
      return;
    }
    try {
      const presetResponse = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/presets?upload_type=${productPage}`
      );
      const savedPresets = await presetResponse.json();
      setUserPresets(savedPresets);
    } catch (e) {
      console.log("ERROR getting user analysis presets");
    }
  };

  const resetState = () => {
    setResetDragDrop(true);
    setFiles([]);
    updateCheckParams(false); // this will also reset the analysis params and their error message
    setFailedUploadsMsg(failedUploadsMsg);
    setModalButtons(["Close"]);
    setMinPulse3dVersionForCurrentUploads(getMinP3dVersionForProduct(productPage));
    // in case user added a new preset, want to grab updated list on analysis submission
    getAnalysisPresets();
    setSelectedPresetIdx();
    resetAnalysisParams();
  };

  const resetAnalysisParams = () => {
    setAnalysisParams(getDefaultAnalysisParams());
    setAnalysisPresetName("");
    setSavePresetChecked(false);
    setSelectedPresetIdx();
  };

  const updateCheckParams = (newCheckedParams) => {
    if (checkedParams && !newCheckedParams) {
      // if unchecking, reset all params
      resetAnalysisParams();
      setParamErrors({});
    }
    setCheckedParams(newCheckedParams);
  };

  const formatTupleParams = (firstParam, secondParam) => {
    // convert factors that aren't specified to null
    if (firstParam === "") {
      firstParam = null;
    }
    if (secondParam === "") {
      secondParam = null;
    }
    let factors = [firstParam, secondParam];

    if (factors.every((v) => !v)) {
      // if both factors are null, return null instead of an array
      return null;
    }
    return factors;
  };

  const getNullIfEmpty = (val) => {
    return val === "" ? null : val;
  };

  const getJobParams = (uploadId) => {
    const {
      normalizeYAxis,
      showStimSheet,
      baseToPeak,
      peakToBase,
      maxY,
      prominenceFactorPeaks,
      prominenceFactorValleys,
      relativeProminenceFactor,
      noiseProminenceFactor,
      widthFactorPeaks,
      widthFactorValleys,
      minPeakHeight,
      maxPeakFreq,
      valleySearchDuration,
      upslopeDuration,
      upslopeNoiseAllowance,
      twitchWidths,
      selectedPulse3dVersion,
      stiffnessFactor,
      wellsWithFlippedWaveforms,
      platemapName,
      wellGroups,
      stimWaveformFormat,
      dataType,
      minPeakWidth,
      maxPeakWidth,
      normalizationMethod,
      relaxationSearchLimit,
      nmjSingleAxisSensing,
      highFidelityMagnetProcessing,
    } = analysisParams;

    const version =
      selectedPulse3dVersion === "" || !selectedPulse3dVersion ? pulse3dVersions[0] : selectedPulse3dVersion;

    const requestBody = {
      // pulse3d versions are currently sorted in desc order, so pick the first (latest) version as the default
      version,
    };

    if (uploadId) {
      requestBody.upload_id = uploadId;
    }

    if (twitchWidths === "") {
      requestBody.twitch_widths = null;
    } else {
      // remove duplicates and sort
      requestBody.twitch_widths = Array.from(new Set(twitchWidths)).sort((a, b) => a - b);
    }

    for (const [name, value] of [
      ["normalize_y_axis", normalizeYAxis],
      ["max_y", maxY],
      ["include_stim_protocols", showStimSheet],
    ]) {
      if (productPage === "mantarray") {
        requestBody[name] = getNullIfEmpty(value);
      } else {
        requestBody[name] = null;
      }
    }

    if (semverGte(version, "0.30.1")) {
      if (productPage === "mantarray") {
        requestBody.stiffness_factor = getNullIfEmpty(stiffnessFactor);
        requestBody.inverted_post_magnet_wells = getNullIfEmpty(wellsWithFlippedWaveforms);
      } else {
        requestBody.stiffness_factor = null;
        requestBody.inverted_post_magnet_wells = null;
      }
    }
    if (semverGte(version, "0.30.3")) {
      requestBody.well_groups = Object.keys(wellGroups).length === 0 ? null : wellGroups;
    }
    if (semverGte(version, "0.30.5")) {
      if (productPage === "mantarray") {
        requestBody.stim_waveform_format = getNullIfEmpty(stimWaveformFormat);
      } else {
        requestBody.stim_waveform_format = null;
      }
    }
    if (semverGte(version, "0.32.2")) {
      // don't add name if it's the original filename or if it's empty
      const useOriginalName =
        !reanalysis ||
        files?.length !== 1 ||
        analysisParams.nameOverride === "" ||
        analysisParams.nameOverride === removeFileExt(files[0].filename);
      requestBody.name_override = useOriginalName ? null : analysisParams.nameOverride;
    }
    if (semverGte(version, "0.34.2")) {
      if (productPage === "nautilai") {
        requestBody.data_type = getNullIfEmpty(dataType);
      } else {
        requestBody.data_type = null;
      }
    }

    if (semverGte(version, "0.33.2")) {
      for (const [name, value] of [
        ["relative_prominence_factor", relativeProminenceFactor],
        ["noise_prominence_factor", noiseProminenceFactor],
        ["height_factor", minPeakHeight],
        ["max_frequency", maxPeakFreq],
        ["valley_search_duration", valleySearchDuration],
        ["upslope_duration", upslopeDuration],
        ["upslope_noise_allowance_duration", upslopeNoiseAllowance],
      ]) {
        requestBody[name] = getNullIfEmpty(value);
      }

      requestBody.width_factors = formatTupleParams(minPeakWidth, maxPeakWidth);
      // need to convert all these params from ms to s
      for (const name of ["valley_search_duration", "upslope_duration", "upslope_noise_allowance_duration"]) {
        if (requestBody[name] !== null) {
          requestBody[name] /= 1000;
        }
      }
      if (requestBody.width_factors !== null) {
        requestBody.width_factors = requestBody.width_factors.map((width) =>
          width !== null ? width / 1000 : null
        );
      }
    } else {
      requestBody.prominence_factors = formatTupleParams(prominenceFactorPeaks, prominenceFactorValleys);
      requestBody.width_factors = formatTupleParams(widthFactorPeaks, widthFactorValleys);
    }

    if (semverGte(version, "1.0.0")) {
      if (productPage === "nautilai") {
        requestBody.normalization_method = normalizationMethod === "None" ? null : normalizationMethod;
        requestBody.detrend = analysisParams.detrend;
      } else {
        requestBody.normalization_method = null;
        requestBody.detrend = null;
      }
    }

    if (semverGte(version, "1.0.8")) {
      requestBody.platemap_name = getNullIfEmpty(platemapName);
    }

    if (semverGte(version, "2.0.0")) {
      requestBody.relaxation_search_limit_secs = getNullIfEmpty(relaxationSearchLimit);
      if (!semverGte(version, "3.0.0")) {
        // this param was removed in v3.0.0
        requestBody.nmj_single_axis_sensing = nmjSingleAxisSensing;
      }
    } else {
      requestBody.baseline_widths_to_use = formatTupleParams(baseToPeak, peakToBase);
    }

    if (semverGte(version, "3.0.0")) {
      requestBody.high_fidelity_magnet_processing = highFidelityMagnetProcessing;
    }

    // format windows
    let windows = analysisParams.windows.map(({ start, end }) => {
      return { start: getNullIfEmpty(start), end: getNullIfEmpty(end) };
    });
    if (windows.length === 0) {
      windows = [{ start: null, end: null }];
    }
    // create one request body per window
    let requestBodies = windows.map(({ start, end }) => {
      const requestBodyWithWindows = { ...requestBody };
      requestBodyWithWindows.start_time = start;
      requestBodyWithWindows.end_time = end;
      return requestBodyWithWindows;
    });

    return requestBodies;
  };

  const postNewJob = async (uploadId, filename) => {
    let requestBodies;
    try {
      requestBodies = getJobParams(uploadId);
    } catch (e) {
      console.log("ERROR creating job params", e);
      failedUploadsMsg.push(filename);
      return;
    }
    requestBodies.map(async (requestBody) => {
      try {
        const jobResponse = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs`, {
          method: "POST",
          body: JSON.stringify(requestBody),
        });

        const jobData = await jobResponse.json();
        // 403 gets returned in quota limit reached responses modal gets handled in ControlPanel
        if (jobData.error && jobData.error === "UsageError") {
          console.log("ERROR starting job because customer job limit has been reached");
          setUsageModalLabels(modalObj.jobsReachedDuringSession);
          setUsageModalState(true);
        } else if (jobData.usage_quota.jobs_reached) {
          setUsageModalLabels(modalObj.jobsReachedAfterAnalysis);
          setUsageModalState(true);
        } else if (jobResponse.status !== 200 || (jobData.error && jobData.error == "AuthorizationError")) {
          console.log("ERROR posting new job");
          failedUploadsMsg.push(filename);
        }
      } catch (e) {
        console.log("ERROR posting new job", e);
        failedUploadsMsg.push(filename);
      }
    });
  };

  const submitNewAnalysis = async () => {
    if (files.length > 0) {
      await handleNewAnalysis(files);
    }
    resetState();
  };

  const checkFileContents = async () => {
    // if reanalysis then there are no files to check
    if (reanalysis) {
      return;
    }

    var JSZip = require("jszip");

    const asyncFilter = async (arr, predicate) =>
      Promise.all(arr.map(predicate)).then((results) => arr.filter((_v, index) => results[index]));

    let badFilesUpdate = await asyncFilter(files, async (file) => {
      // if the file is falsey then it is invalid and there is nothing more to do
      if (!file?.name) {
        return true;
      }

      let isValidUpload;

      try {
        if (file.type.includes("zip")) {
          const zip = new JSZip();
          const { files: loadedFiles } = await zip.loadAsync(file);
          const dirs = Object.values(loadedFiles).filter(({ dir }) => dir);
          const onlyOneDir = dirs.length === 0 || dirs.length === 1;

          const numXlsxInFile = Object.keys(loadedFiles).filter(
            (filename) => filename.includes(".xlsx") && !filename.includes("__MACOSX")
          ).length;
          const numH5InFile = Object.keys(loadedFiles).filter(
            (filename) => filename.includes(".h5") && !filename.includes("__MACOSX")
          ).length;

          if ([numXlsxInFile, numH5InFile].filter((count) => count > 0).length != 1) {
            isValidUpload = false;
            // If multiple file types in the same zip, it is an invalid file. The zip must contain exactly one of the supported file types
          } else {
            let zipContainsValidNumFiles, isValidUploadTypeForProduct;
            if (numH5InFile > 0) {
              zipContainsValidNumFiles = numH5InFile === 24 || numH5InFile === 48;
              isValidUploadTypeForProduct = productPage === "mantarray";
            } else {
              // xlsx
              zipContainsValidNumFiles = numXlsxInFile > 0;
              isValidUploadTypeForProduct = productPage === "nautilai";
            }

            isValidUpload = onlyOneDir && zipContainsValidNumFiles && isValidUploadTypeForProduct;
          }
        } else if (file.name.endsWith("xlsx")) {
          // xlsx uploads only supported for nautilai
          isValidUpload = productPage === "nautilai";
        } else if (file.name.endsWith("parquet")) {
          // parquet files only currently supported for nautilai, but should be supported by other products in the future
          isValidUpload = productPage === "nautilai";
        } else {
          // all other file types are not valid
          isValidUpload = false;
        }
      } catch (e) {
        console.log(`ERROR unable to read file ${file.filename}:`, e);
        isValidUpload = false;
        failedUploadsMsg.push(file.filename);
      }

      return !isValidUpload;
    });

    setBadFiles([...badFilesUpdate]);

    for (let i = 0; i < badFilesUpdate.length; i++) {
      const matchingIdx = files.findIndex(({ name }) => name === badFilesUpdate[i].name);
      files.splice(matchingIdx, 1);
      setFiles([...files]);
    }
  };

  const handleNewAnalysis = async (files) => {
    // update state to trigger in progress spinner over submit button
    if (files.length > 0) {
      setInProgress(true);

      for (const file of files) {
        //check file is in uploads list
        const fileIsInList = uploads.some((upload) => upload.id === file.id);

        if (file instanceof File) {
          if (file.size <= MAX_WHOLE_UPLOAD_SIZE) {
            await uploadFileWhole(file);
          } else {
            await uploadFileMultipart(file);
          }
        } else if (fileIsInList) {
          await postNewJob(file.id, file.filename);
        }
      }

      try {
        // just logging error occurred, doesn't block rest of analysis
        if (savePresetChecked) {
          await saveAnalysisPreset();
        }
      } catch (e) {
        console.log("ERROR saving analysis preset");
      }

      // open error modal notifying which files failed if any, otherwise display success text
      if (failedUploadsMsg.length > 1) {
        setModalState(true);
      } else {
        setUploadSuccess(true);
      }
      setInProgress(false);
    }
  };

  const uploadFileWhole = async (file) => {
    let fileReader = new FileReader();
    const filename = file.name;

    try {
      let fileHash;
      try {
        // Tanner (8/11/21): Need to use a promise here since FileReader API does not support using async functions, only callbacks
        fileHash = await new Promise((resolve, reject) => {
          fileReader.onload = function (e) {
            if (file.size != e.target.result.byteLength) {
              console.log(
                "ERROR:</strong> Browser reported success but could not read the file until the end."
              );
              reject();
            }

            resolve(SparkMD5.ArrayBuffer.hash(e.target.result));
          };

          fileReader.onerror = function () {
            console.log(
              "ERROR: FileReader onerror was triggered, maybe the browser aborted due to high memory usage."
            );
            reject();
          };

          fileReader.readAsArrayBuffer(file);
        });
      } catch (e) {
        failedUploadsMsg.push(filename);
        return;
      }

      const uploadResponse = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads`, {
        method: "POST",
        body: JSON.stringify({
          filename,
          md5s: hexToBase64(fileHash),
          upload_type: productPage,
          auto_upload: false,
        }),
      });
      if (uploadResponse.status !== 200) {
        // break flow if initial request returns error status code
        console.log("ERROR uploading file metadata to DB:  ", await uploadResponse.json());
        failedUploadsMsg.push(filename);
        return;
      }

      const data = await uploadResponse.json();

      if (data.error && data.error == "UsageError") {
        console.log("ERROR uploading file because customer upload limit has been reached");
        setUsageModalLabels(modalObj.uploadsReachedDuringSession);
        setUsageModalState(true);
        return;
      }
      const uploadDetails = data.params;
      const uploadId = data.id;

      const formData = new FormData();
      Object.entries(uploadDetails.fields).forEach(([k, v]) => {
        formData.append(k, v);
      });
      formData.append("file", file);

      let uploadPostRes = null;
      for (const attemptNum = 1; attemptNum <= 5; attemptNum++) {
        try {
          uploadPostRes = await fetch(uploadDetails.url, {
            method: "POST",
            body: formData,
          });
        } catch (e) {
          console.log(`ERROR attempt #${attemptNum} uploading file to s3:  `, e);
          continue;
        }
        break;
      }
      if (uploadPostRes === null) {
        console.log("ERROR Max num upload attempts reached");
        await handleFailedUploadToS3(uploadId);
        failedUploadsMsg.push(filename);
        return;
      }
      if (uploadPostRes.status !== 204) {
        let errMsg = "Error getting response body as text";
        try {
          errMsg = parseS3XmlErrorCode(await uploadPostRes.text());
        } catch {}
        console.log(`ERROR uploading file to s3: ${uploadPostRes.status} ${errMsg}`);
        await handleFailedUploadToS3(uploadId);
        failedUploadsMsg.push(filename);
        return;
      }

      await postNewJob(uploadId, filename);
    } catch (e) {
      failedUploadsMsg.push(filename);
      console.log("ERROR handling new file upload:  ", e);
    }
  };

  const handleFailedUploadToS3 = async (uploadId) => {
    const uploadsURL = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads?upload_ids=${uploadId}`;

    let uploadsResponse;
    try {
      uploadsResponse = await fetch(uploadsURL, {
        method: "DELETE",
      });
    } catch (e) {
      console.log(`ERROR deleting DB entry for failed upload with ID: ${uploadId}`, e);
    }
    if (uploadsResponse.status !== 200) {
      console.log(
        `ERROR (${uploadsResponse.status}) deleting DB entry for failed upload with ID: ${uploadId}`
      );
    }
  };

  const uploadFileMultipart = async (file) => {
    const handleError = (e) => {
      console.log(`ERROR uploading file ${file.name}`, e);
      failedUploadsMsg.push(file.name);
    };
    try {
      // initiate multipart upload
      const [totalHash, chunkHashes] = await fileMd5sChunks(file);
      const mpUploadRes = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads/multipart`, {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          md5s: totalHash,
          md5s_parts: chunkHashes,
          upload_type: productPage,
          auto_upload: false,
        }),
      });
      let mpUploadResData = {};
      try {
        mpUploadResData = await mpUploadRes.json();
      } catch {
        mpUploadResData = { error: "Failed to parse response body as json" };
      }
      if (mpUploadRes.status !== 200) {
        console.log("ERROR getting multipart upload details: ", mpUploadResData);
        handleError(mpUploadResData);
        return;
      }
      if (mpUploadResData.error === "UsageError") {
        console.log("ERROR getting multipart upload details because customer upload limit has been reached");
        handleError(mpUploadResData.error);
        setUsageModalLabels(modalObj.uploadsReachedDuringSession);
        setUsageModalState(true);
        return;
      }

      let urls = mpUploadResData.urls;
      if (urls.length !== chunkHashes.length) {
        handleError("incorrect number of parts in multipart upload details");
        return;
      }

      // upload chunks
      const uploadParts = [];
      let chunkStart = 0;
      let prevRefreshTimestamp = Date.now();
      for (const partIdx = 0; partIdx < urls.length; partIdx++) {
        const millisSincePrevUpload = Date.now() - prevRefreshTimestamp;
        const minsSincePrevUpload = millisSincePrevUpload / (1000 * 60);
        if (minsSincePrevUpload > 25) {
          // TODO refresh tokens, update prevRefreshTimestamp if successful
        }

        let chunkEnd = Math.min(file.size, chunkStart + MULTIPART_UPLOAD_CHUNK_SIZE);

        let uploadPartRes = null;
        for (const attemptNum = 1; attemptNum <= 200; attemptNum++) {
          try {
            uploadPartRes = await fetch(urls[partIdx], {
              method: "PUT",
              headers: {
                "Content-MD5": chunkHashes[partIdx],
              },
              body: file.slice(chunkStart, chunkEnd),
            });
          } catch (e) {
            console.log(
              `ERROR attempt ${attemptNum} uploading file part (${partIdx + 1}/${urls.length}) to s3:  `,
              e
            );
            continue;
          }
          break;
        }
        if (uploadPartRes === null) {
          handleError(`Max num upload attempts reached for part (${partIdx + 1}/${urls.length})`);
          return;
        }

        if (uploadPartRes.status !== 200) {
          let errMsg = "Error getting response body as text";
          try {
            errMsg = parseS3XmlErrorCode(await uploadPartRes.text());
          } catch {}
          handleError(
            `ERROR uploading file part (${partIdx + 1}/${urls.length}) to s3: ${uploadPartRes.status} ${
              parseS3XmlErrorCode(bodyText) || bodyTextErrorMsg
            }`
          );
          return;
        }
        const etag = uploadPartRes.headers.get("ETag");
        if (etag === null) {
          handleError(
            `etag header missing on upload file part response (${partIdx + 1}/${urls.length}) from s3`
          );
          return;
        }

        uploadParts.push({ ETag: etag, PartNumber: partIdx + 1 });
        chunkStart = chunkEnd;
      }

      const completeMpUploadRes = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads/multipart/complete`,
        {
          method: "PUT",
          body: JSON.stringify({
            id: mpUploadResData.id,
            parts: uploadParts,
          }),
        }
      );
      let completeMpUploadResData = {};
      try {
        completeMpUploadResData = await completeMpUploadRes.json();
      } catch {
        completeMpUploadResData = { error: "Failed to parse response body as json" };
      }
      if (completeMpUploadRes.status !== 204) {
        console.log("ERROR completing multipart upload: ", completeMpUploadResData);
        handleError(completeMpUploadResData);
        return;
      }
    } catch (e) {
      handleError(e);
    }
  };

  const handleDropDownSelect = (idx) => {
    if (idx !== -1) {
      const newSelection = uploads[idx];
      const newFiles = [...files, newSelection];
      setFiles(newFiles);
      // clear nameOverride anytime user changes file selection
      setAnalysisParams({
        ...analysisParams,
        nameOverride: "",
      });
    }
  };

  const removeFileExt = (filename) => {
    const filenameNoExt = filename.split(".");
    filenameNoExt.pop();

    return filenameNoExt.join(".");
  };

  const saveAnalysisPreset = async () => {
    // we don't want name override to be saved in presets
    const defaultParams = getDefaultAnalysisParams();
    const analysisParamsToSave = { ...analysisParams, nameOverride: defaultParams.nameOverride };
    await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/presets`, {
      method: "POST",
      body: JSON.stringify({
        name: analysisPresetName,
        analysis_params: analysisParamsToSave,
        upload_type: productPage,
      }),
    });
  };

  const handleClose = async (idx) => {
    // if user chooses to proceed with upload when some files were flagged as bad
    if (idx === 1) {
      const filteredFiles = files.filter((f) => !failedUploadsMsg.includes(f.name));
      await handleNewAnalysis(filteredFiles);
    }
    // goes after because this dependency triggers reset
    setModalState(false);
    setFailedUploadsMsg([defaultUploadErrorLabel]);
  };

  return (
    <Container>
      <Uploads>
        <Header>Run Analysis</Header>
        {reanalysis ? (
          <>
            <div
              style={{
                width: "50%",
                border: "2px solid var(--dark-gray)",
                borderRadius: "5px",
                marginTop: "2rem",
                backgroundColor: "var(--light-gray)",
              }}
            >
              <DropDownContainer>
                <div style={{ backgroundColor: "white" }}>
                  <InputDropdownWidget
                    label="Select Recording"
                    options={formattedUploads}
                    handleSelection={handleDropDownSelect}
                    reset={files.length === 0}
                    width={500}
                    disabled={inProgress}
                  />
                </div>
              </DropDownContainer>
              <div style={{ textAlign: "center", marginTop: "10px", fontSize: "18px" }}>
                <b>{`Selected Files (${files?.length || 0}):`}</b>
              </div>
              {files?.length > 0 ? (
                <ul>
                  {files.map((f, idx) => {
                    return (
                      <li key={`reanalysis-file-${idx}`}>
                        <div style={{ display: "flex", flexDirection: "col" }}>
                          <div style={{ width: "80%" }}>{f.filename}</div>
                          <RemoveButton
                            onClick={(e) => {
                              e.preventDefault();
                              files.splice(idx, 1);
                              setFiles([...files]);
                              // clear nameOverride anytime user changes file selection
                              setAnalysisParams({
                                ...analysisParams,
                                nameOverride: "",
                              });
                            }}
                          >
                            Remove
                          </RemoveButton>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <div style={{ textAlign: "center", marginBlock: "16px" }}>None</div>
              )}
            </div>
            {usageQuota && usageQuota.limits && parseInt(usageQuota.limits.jobs) !== -1 && (
              <UploadCreditUsageInfo>
                Re-analysis will run once per window per selected file, consuming 1 analysis credit each
                except for the first re-analysis of a given file.
              </UploadCreditUsageInfo>
            )}
          </>
        ) : (
          <>
            <FileDragDrop
              handleFileChange={(files) => setFiles(Object.values(files))}
              dropZoneText={dropZoneText}
              fileSelection={files}
              setResetDragDrop={setResetDragDrop}
              resetDragDrop={resetDragDrop}
              fileTypes={["zip", "xlsx", "parquet"]}
            />
            {usageQuota && usageQuota.limits && parseInt(usageQuota.limits.jobs) !== -1 && (
              <UploadCreditUsageInfo>
                Analysis will run once per window per successfully uploaded file, consuming 1 analysis credit
                each.
              </UploadCreditUsageInfo>
            )}
          </>
        )}
        <AnalysisParamForm
          errorMessages={paramErrors}
          checkedParams={checkedParams}
          setCheckedParams={updateCheckParams}
          paramErrors={paramErrors}
          setParamErrors={setParamErrors}
          setAnalysisParams={setAnalysisParams}
          analysisParams={analysisParams}
          setWellGroupErr={setWellGroupErr}
          windowsErrors={windowsErrors}
          setWindowsErrors={setWindowsErrors}
          reanalysis={reanalysis}
          numFiles={files?.length}
          minPulse3dVersionAllowed={minPulse3dVersionForCurrentUploads}
          userPresetOpts={{
            userPresets,
            setUserPresets,
            selectedPresetIdx,
            setSelectedPresetIdx,
            savePresetChecked,
            setSavePresetChecked,
            setAnalysisPresetName,
            analysisPresetName,
          }}
        />
        <ButtonContainer>
          {uploadSuccess && <SuccessText>Upload Successful!</SuccessText>}
          <ButtonWidget
            width="200px"
            height="50px"
            position="relative"
            borderRadius="3px"
            label="Reset"
            clickFn={resetState}
          />
          <ButtonWidget
            width="200px"
            height="50px"
            position="relative"
            borderRadius="3px"
            left="10px"
            backgroundColor={isButtonDisabled ? "var(--dark-gray)" : "var(--dark-blue)"}
            disabled={isButtonDisabled}
            inProgress={inProgress}
            label="Submit"
            clickFn={submitNewAnalysis}
          />
        </ButtonContainer>
      </Uploads>
      <ModalWidget
        open={modalState}
        labels={failedUploadsMsg}
        buttons={modalButtons}
        closeModal={handleClose}
        header="Error Occurred"
      />
      <ModalWidget
        open={usageModalState}
        labels={usageModalLabels.messages}
        closeModal={() => {
          setUsageModalState(false);
          router.replace("/uploads", undefined, { shallow: true });
        }}
        header={usageModalLabels.header}
      />
    </Container>
  );
}

UploadForm.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
