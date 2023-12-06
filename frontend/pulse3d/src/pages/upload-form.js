import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import AnalysisParamForm from "@/components/uploadForm/AnalysisParamForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import FileDragDrop from "@/components/uploadForm/FileDragDrop";
import SparkMD5 from "spark-md5";
import { hexToBase64 } from "../utils/generic";
import { useRouter } from "next/router";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DashboardLayout, { UploadsContext } from "@/components/layouts/DashboardLayout";
import semverGte from "semver/functions/gte";
import InputDropdownWidget from "@/components/basicWidgets/InputDropdownWidget";
import { AuthContext } from "./_app";

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
  margin-top: 2rem;
`;

const dropZoneText = "CLICK HERE or DROP";
const defaultUploadErrorLabel =
  "Something went wrong while attempting to start the analysis for the following file(s):";
const defaultBadFilesLabel =
  "The following file(s) cannot be uploaded because they either contain multiple recordings or do not have the correct number of files.";

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

const isReanalysisPage = (router) => {
  return (
    typeof router.query.id === "string" && router.query.id.toLowerCase() === "re-analyze existing upload"
  );
};

export default function UploadForm() {
  const { uploads, pulse3dVersions, defaultUploadForReanalysis } = useContext(UploadsContext);

  const getDefaultAnalysisParams = () => {
    return {
      normalizeYAxis: "",
      baseToPeak: "",
      peakToBase: "",
      maxY: "",
      twitchWidths: "",
      startTime: "",
      endTime: "",
      stiffnessFactor: null,
      selectedPulse3dVersion: pulse3dVersions[0] || "", // Tanner (9/15/22): The pulse3d version technically isn't a param, but it lives in the same part of the form as the params
      wellsWithFlippedWaveforms: "",
      showStimSheet: "",
      wellGroups: {},
      stimWaveformFormat: "",
      nameOverride: "",
      dataType: null,
      // original advanced params
      prominenceFactorPeaks: "",
      prominenceFactorValleys: "",
      widthFactorPeaks: "",
      widthFactorValleys: "",
      // noise based advanced params
      relativeProminenceFactor: "",
      noiseProminenceFactor: "",
      minPeakWidth: "",
      maxPeakWidth: "",
      minPeakHeight: "",
      maxPeakFreq: "",
      valleySearchDuration: "",
      upslopeDuration: "",
      upslopeNoiseAllowance: "",
    };
  };

  const router = useRouter();
  const { usageQuota, productPage } = useContext(AuthContext);

  const [files, setFiles] = useState(defaultUploadForReanalysis ? [defaultUploadForReanalysis] : []);
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
  const [wellGroupErr, setWellGroupErr] = useState(false);
  const [creditUsageAlert, setCreditUsageAlert] = useState(false);
  const [alertShowed, setAlertShowed] = useState(false);
  const [reanalysis, setReanalysis] = useState(isReanalysisPage(router));
  const [xlsxFilePresent, setXlsxFilePresent] = useState(false);
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
      wellGroupErr;

    setIsButtonDisabled(checkConditions);

    setCreditUsageAlert(
      !alertShowed && //makesure modal shows up only once
        !checkConditions &&
        reanalysis && // modal only shows up in re-analyze tab
        usageQuota && // undefined check
        usageQuota.limits && // undefined check
        parseInt(usageQuota.limits.jobs) !== -1 && // check that usage is not unlimited
        files.length > 0 && // undefined check
        files[0].created_at !== files[0].updated_at
      // if time updated and time created are different then free analysis has already been used and a re-analyze will use a credit
    );
  }, [paramErrors, files, inProgress, wellGroupErr]);

  useEffect(() => {
    populateFormWithPresetParams();
  }, [selectedPresetIdx]);

  useEffect(() => {
    // resets upload status when user makes changes
    if (
      (files.length > 0 && files[0] instanceof File) ||
      JSON.stringify(analysisParams) != JSON.stringify(getDefaultAnalysisParams())
    ) {
      setUploadSuccess(false);
    }
  }, [files, analysisParams]);

  useEffect(() => {
    // check for incorrect files and let user know
    checkFileContents();
  }, [files]);

  useEffect(() => {
    // grab list of user presets on initial load
    // this gets called again in resetState when an analysis is submitted
    getAnalysisPresets();
  }, []);

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
        // checking that the param exists incase params change over time, do not directly replace assuming all values match
        // and don't update if already default value
        if (param in currentParams && presetParams[param] !== currentParams[param]) {
          currentParams[param] = presetParams[param];
          // protect against deprecated pulse3d versions
          if (param == "selectedPulse3dVersion" && !pulse3dVersions.includes(presetParams[param])) {
            currentParams[param] = pulse3dVersions[0];
          }
        }
      }

      setAnalysisParams(currentParams);
    }
  };

  const getAnalysisPresets = async () => {
    try {
      const presetResponse = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/presets`);
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
    setXlsxFilePresent(false);
    // in case user added a new preset, want to grab updated list on analysis submission
    getAnalysisPresets();
    setSelectedPresetIdx();
    resetAnalysisParams();
  };

  const resetAnalysisParams = () => {
    setAnalysisParams(getDefaultAnalysisParams());
    setAnalysisPresetName("");
    setSavePresetChecked(false);
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
    firstParam = firstParam === "" ? null : parseFloat(firstParam);
    secondParam = secondParam === "" ? null : parseFloat(secondParam);

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
      startTime,
      endTime,
      selectedPulse3dVersion,
      stiffnessFactor,
      wellsWithFlippedWaveforms,
      wellGroups,
      stimWaveformFormat,
      dataType,
    } = analysisParams;

    const version =
      selectedPulse3dVersion === "" || !selectedPulse3dVersion ? pulse3dVersions[0] : selectedPulse3dVersion;

    const requestBody = {
      baseline_widths_to_use: formatTupleParams(baseToPeak, peakToBase),
      // pulse3d versions are currently sorted in desc order, so pick the first (latest) version as the default
      version,
    };

    if (uploadId) {
      requestBody.upload_id = uploadId;
    }

    for (const [name, value] of [
      ["normalize_y_axis", normalizeYAxis],
      ["twitch_widths", twitchWidths],
      ["start_time", startTime],
      ["end_time", endTime],
      ["max_y", maxY],
      ["include_stim_protocols", showStimSheet],
    ]) {
      requestBody[name] = getNullIfEmpty(value);
    }

    if (semverGte(version, "0.30.1")) {
      requestBody.stiffness_factor = getNullIfEmpty(stiffnessFactor);
      requestBody.inverted_post_magnet_wells = getNullIfEmpty(wellsWithFlippedWaveforms);
    }
    if (semverGte(version, "0.30.3")) {
      requestBody.well_groups = Object.keys(wellGroups).length === 0 ? null : wellGroups;
    }
    if (semverGte(version, "0.30.5")) {
      requestBody.stim_waveform_format = getNullIfEmpty(stimWaveformFormat);
    }
    if (semverGte(version, "0.32.2")) {
      // don't add name if it's the original filename or if it's empty
      const useOriginalName =
        analysisParams.nameOverride === "" ||
        analysisParams.nameOverride === removeFileExt(files[0].filename);
      requestBody.name_override = useOriginalName ? null : analysisParams.nameOverride;
    }
    if (semverGte(version, "0.34.2")) {
      requestBody.data_type = getNullIfEmpty(dataType);
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
        requestBody.width_factors = requestBody.width_factors.map((width) => {
          width !== null ? width / 1000 : null;
        });
      }
    } else {
      requestBody.prominence_factors = formatTupleParams(prominenceFactorPeaks, prominenceFactorValleys);
      requestBody.width_factors = formatTupleParams(widthFactorPeaks, widthFactorValleys);
    }

    return requestBody;
  };

  const postNewJob = async (uploadId, filename) => {
    try {
      const requestBody = getJobParams(uploadId);
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
        failedUploadsMsg.push(filename);
        console.log("ERROR posting new job");
      }
    } catch (e) {
      failedUploadsMsg.push(filename);
      console.log("ERROR posting new job", e);
    }
  };

  const submitNewAnalysis = async () => {
    if (files.length > 0) {
      await handleNewAnalysis(files);
    }
    resetState();
  };

  const checkFileContents = async () => {
    var JSZip = require("jszip");
    let filteredFiles;
    if (!reanalysis) {
      const asyncFilter = async (arr, predicate) =>
        Promise.all(arr.map(predicate)).then((results) => arr.filter((_v, index) => results[index]));

      let xlsxInFile = false;
      filteredFiles = await asyncFilter(files, async (file) => {
        //only run these checks if is zip file
        try {
          if (file && file.type.includes("zip")) {
            const zip = new JSZip();
            const { files: loadedFiles } = await zip.loadAsync(file);
            const dirs = Object.values(loadedFiles).filter(({ dir }) => dir);
            const onlyOneDir = dirs.length === 0 || dirs.length === 1;

            const numXlxsInFile = Object.keys(loadedFiles).filter(
              (filename) => filename.includes(".xlsx") && !filename.includes("__MACOSX")
            ).length;

            const numH5InFile = Object.keys(loadedFiles).filter(
              (filename) => filename.includes(".h5") && !filename.includes("__MACOSX")
            ).length;

            const fileContainsValidNumFiles =
              numH5InFile > 0 ? numH5InFile === 24 || numH5InFile === 48 : numXlxsInFile > 0;

            // not setting xlsxInFile = (numXlxsInFile > 0) because it needs to remain true if ever made true
            if (numXlxsInFile > 0) xlsxInFile = numXlxsInFile;

            return !onlyOneDir || !fileContainsValidNumFiles;
          } else {
            // this will occur when user uploads single well xlsx data
            // not setting xlsxInFile = (numXlxsInFile > 0) because it needs to remain true if ever made true
            xlsxInFile = 1;
          }
        } catch (e) {
          console.log(`ERROR unable to read file: ${file.filename} ${e}`);
          failedUploadsMsg.push(file.filename);
          return true;
        }
      });

      setXlsxFilePresent(xlsxInFile);
      setBadFiles([...filteredFiles]);

      for (let i = 0; i < filteredFiles.length; i++) {
        const matchingIdx = files.findIndex(({ name }) => name === filteredFiles[i].name);
        files.splice(matchingIdx, 1);
        setFiles([...files]);
      }
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
          await uploadFile(file);
        } else if (fileIsInList) {
          await postNewJob(file.id, file.filename);
        }
      }

      try {
        // just logging error occurred, doesn't block rest of analysis
        if (savePresetChecked) await saveAnalysisPreset();
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

  const uploadFile = async (file) => {
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
        failedUploadsMsg.push(filename);
        console.log("ERROR uploading file metadata to DB:  ", await uploadResponse.json());
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

      const uploadPostRes = await fetch(uploadDetails.url, {
        method: "POST",
        body: formData,
      });

      if (uploadPostRes.status === 204) {
        await postNewJob(uploadId, filename);
      } else {
        failedUploadsMsg.push(filename);
        console.log("ERROR uploading file to s3:  ", await uploadPostRes.json());
      }
    } catch (e) {
      // catch all if service worker isn't working
      console.log("ERROR posting to presigned url");
    }
  };

  const handleDropDownSelect = (idx) => {
    setAlertShowed(false);

    let nameOverride = "";
    if (idx === -1) {
      setFiles([]); // must be an array
    } else {
      const newSelection = uploads[idx];
      setFiles([newSelection]);
      nameOverride = removeFileExt(newSelection.filename).join(".");
    }

    setAnalysisParams({
      ...analysisParams,
      nameOverride: nameOverride,
    });
  };

  const removeFileExt = (filename) => {
    const filenameNoExt = filename.split(".");
    filenameNoExt.pop();

    return filenameNoExt;
  };

  const saveAnalysisPreset = async () => {
    await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/presets`, {
      method: "POST",
      body: JSON.stringify({ name: analysisPresetName, analysis_params: analysisParams }),
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
          <DropDownContainer>
            <InputDropdownWidget
              label="Select Recording"
              options={formattedUploads}
              initialOption={defaultUploadForReanalysis ? defaultUploadForReanalysis.filename : null}
              handleSelection={handleDropDownSelect}
              reset={files.length === 0}
              width={500}
              disabled={inProgress}
            />
          </DropDownContainer>
        ) : (
          <>
            <FileDragDrop // TODO figure out how to notify user if they attempt to upload existing recording
              handleFileChange={(files) => setFiles(Object.values(files))}
              dropZoneText={dropZoneText}
              fileSelection={
                files.length > 0 ? files.map(({ name }) => name).join(", ") : "No files selected"
              }
              setResetDragDrop={setResetDragDrop}
              resetDragDrop={resetDragDrop}
            />
            {usageQuota && usageQuota.limits && parseInt(usageQuota.limits.jobs) !== -1 ? (
              <UploadCreditUsageInfo>
                Analysis will run on each successfully uploaded file, consuming 1 analysis credit each.
              </UploadCreditUsageInfo>
            ) : null}
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
          reanalysis={reanalysis}
          xlsxFilePresent={xlsxFilePresent}
          userPresetOpts={{
            userPresets,
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
      <ModalWidget
        open={creditUsageAlert}
        labels={["This re-analysis will consume 1 analysis credit."]}
        closeModal={() => {
          setCreditUsageAlert(false);
          setAlertShowed(true);
        }}
        header={"Attention!"}
      />
    </Container>
  );
}

UploadForm.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
