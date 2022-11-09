import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import AnalysisParamForm from "@/components/uploadForm/AnalysisParamForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import FileDragDrop from "@/components/uploadForm/FileDragDrop";
import SparkMD5 from "spark-md5";
import { hexToBase64 } from "../utils/generic";
import { useRouter } from "next/router";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import DashboardLayout, { UploadsContext } from "@/components/layouts/DashboardLayout";
import semverGte from "semver/functions/gte";

const Container = styled.div`
  width: 85%;
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
  height: 75px;
  line-height: 3;
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
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: 3rem 6rem;
`;

const SuccessText = styled.span`
  color: green;
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
  line-height: 3;
`;

const DropDownContainer = styled.div`
  width: 70%;
  display: flex;
  justify-content: center;
  left: 15%;
  position: relative;
  height: 17%;
  align-items: center;
  top: 5%;
  margin-top: 1rem;
`;

const dropZoneText = "CLICK HERE or DROP single recording ZIP files";
const defaultUploadErrorLabel =
  "Something went wrong while attempting to start the analysis for the following file(s):";
const defaultZipErrorLabel =
  "The following file(s) will not be uploaded because they either contain multiple recordings or do not have the correct number of H5 files.";

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
};
export default function UploadForm() {
  const { uploads, pulse3dVersions } = useContext(UploadsContext);

  const getDefaultAnalysisParams = () => {
    return {
      normalizeYAxis: "",
      baseToPeak: "",
      peakToBase: "",
      maxY: "",
      prominenceFactor: "",
      widthFactor: "",
      twitchWidths: "",
      startTime: "",
      endTime: "",
      stiffnessFactor: null,
      selectedPulse3dVersion: pulse3dVersions[0] || "", // Tanner (9/15/22): The pulse3d version technically isn't a param, but it lives in the same part of the form as the params
    };
  };

  const router = useRouter();
  const [files, setFiles] = useState([]);
  const [formattedUploads, setFormattedUploads] = useState([]);
  const [isButtonDisabled, setIsButtonDisabled] = useState(true);
  const [paramErrors, setParamErrors] = useState({});
  const [inProgress, setInProgress] = useState(false);
  const [modalButtons, setModalButtons] = useState(["Close"]);
  const [failedUploadsMsg, setFailedUploadsMsg] = useState([defaultZipErrorLabel]);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [checkedParams, setCheckedParams] = useState(false);
  const [tabSelection, setTabSelection] = useState(router.query.id);
  const [modalState, setModalState] = useState(false);
  const [usageModalState, setUsageModalState] = useState(false);
  const [usageModalLabels, setUsageModalLabels] = useState(modalObj.uploadsReachedDuringSession);
  const [analysisParams, setAnalysisParams] = useState(getDefaultAnalysisParams());

  const resetAnalysisParams = () => {
    setAnalysisParams(getDefaultAnalysisParams());
  };

  const updateCheckParams = (newCheckedParams) => {
    if (checkedParams && !newCheckedParams) {
      // if unchecking, reset all params
      resetAnalysisParams();
      setParamErrors({});
    }
    setCheckedParams(newCheckedParams);
  };

  useEffect(() => {
    // checks if error value exists, no file is selected, or upload is in progress
    const checkConditions =
      !Object.values(paramErrors).every((val) => val.length === 0) ||
      !((files.length > 0 && files[0] instanceof File) || (uploads && uploads.includes(files[0]))) ||
      inProgress;

    setIsButtonDisabled(checkConditions);
  }, [paramErrors, files, inProgress]);

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
    // reset all params if the user switches between the "re-analyze" and "new upload" versions of this page
    setTabSelection(router.query.id);
    resetState();
  }, [router.query]);

  useEffect(() => {
    if (uploads) {
      const uploadFilenames = uploads.map((upload) => upload.filename).filter((name) => name);

      setFormattedUploads([...uploadFilenames]);
    }
  }, [uploads]);

  const resetState = () => {
    setFiles([]);
    updateCheckParams(false); // this will also reset the analysis params and their error message
    setFailedUploadsMsg(failedUploadsMsg);
    setModalButtons(["Close"]);
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

  const postNewJob = async (uploadId, filename) => {
    try {
      const {
        normalizeYAxis,
        baseToPeak,
        peakToBase,
        maxY,
        prominenceFactorPeaks,
        prominenceFactorValleys,
        widthFactorPeaks,
        widthFactorValleys,
        twitchWidths,
        startTime,
        endTime,
        selectedPulse3dVersion,
        stiffnessFactor,
      } = analysisParams;

      const version =
        selectedPulse3dVersion === "" || !selectedPulse3dVersion
          ? pulse3dVersions[0]
          : selectedPulse3dVersion;

      const requestBody = {
        upload_id: uploadId,
        normalize_y_axis: normalizeYAxis === "" ? null : normalizeYAxis,
        baseline_widths_to_use: formatTupleParams(baseToPeak, peakToBase),
        prominence_factors: formatTupleParams(prominenceFactorPeaks, prominenceFactorValleys),
        width_factors: formatTupleParams(widthFactorPeaks, widthFactorValleys),
        twitch_widths: twitchWidths === "" ? null : twitchWidths,
        start_time: startTime === "" ? null : startTime,
        end_time: endTime === "" ? null : endTime,
        // pulse3d versions are currently sorted in desc order, so pick the first (latest) version as the default
        version,
      };

      if (semverGte(version, "0.25.0")) {
        requestBody.max_y = maxY === "" ? null : maxY;
      }
      if (semverGte(version, "0.27.0")) {
        requestBody.stiffness_factor = stiffnessFactor === "" ? null : stiffnessFactor;
      }
      const jobResponse = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs`, {
        method: "POST",
        body: JSON.stringify(requestBody),
      });

      const jobData = await jobResponse.json();
      // 403 gets returned in quota limit reached responses
      // modal gets handled in ControlPanel
      if (jobData.usage_error) {
        console.log("ERROR starting job because customer job limit has been reached");
        setUsageModalLabels(modalObj.jobsReachedDuringSession);
        setUsageModalState(true);
      } else if (jobResponse.status !== 200) {
        failedUploadsMsg.push(filename);
        console.log("ERROR posting new job: ", await jobResponse.json());
      }
    } catch (e) {
      failedUploadsMsg.push(filename);
      console.log("ERROR posting new job", e);
    }
  };

  const submitNewAnalysis = async () => {
    await checkForMultiRecZips();
    resetState();
  };

  const checkForMultiRecZips = async () => {
    var JSZip = require("jszip");

    if (tabSelection === "Analyze New Files") {
      const asyncFilter = async (arr, predicate) =>
        Promise.all(arr.map(predicate)).then((results) => arr.filter((_v, index) => results[index]));

      const badZipfiles = await asyncFilter(files, async (file) => {
        try {
          const zip = new JSZip();
          const { files: loadedFiles } = await zip.loadAsync(file);

          const dirs = Object.values(loadedFiles).filter(({ dir }) => dir);
          const onlyOneRec = dirs.length === 0 || dirs.length === 1;

          const numFilesInRecording = Object.keys(loadedFiles).filter(
            (filename) => filename.includes(".h5") && !filename.includes("__MACOSX")
          ).length;

          // Beta 1 recordings will contain 24 files, Beta 2 and V1 recordings will contain 48
          const recordingContainsValidNumFiles = numFilesInRecording === 24 || numFilesInRecording === 48;
          return !onlyOneRec || !recordingContainsValidNumFiles;
        } catch (e) {
          console.log(`ERROR unable to read zip file: ${file.filename} ${e}`);
          failedUploadsMsg.push(file.filename);
          return true;
        }
      });
      if (badZipfiles.length > 0) {
        // give users the option to proceed with clean files if any, otherwise just close
        setModalButtons(badZipfiles.length !== files.length ? ["Cancel", "Proceed"] : ["Close"]);

        // add files to modal to notify user which files are bad
        setFailedUploadsMsg([defaultZipErrorLabel, ...badZipfiles.map((f) => f.name)]);
        setModalState(true);
        return;
      }
    }

    await handleNewAnalysis(files);
  };

  const handleNewAnalysis = async (files) => {
    // update state to trigger in progress spinner over submit button
    if (files.length > 0) {
      setInProgress(true);

      for (const file of files) {
        if (file instanceof File) {
          await uploadFile(file);
        } else if (uploads.includes(file)) {
          await postNewJob(file.id, file.filename);
        }
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
          upload_type: "pulse3d",
        }),
      });

      if (uploadResponse.status !== 200) {
        // break flow if initial request returns error status code
        failedUploadsMsg.push(filename);
        console.log("ERROR uploading file metadata to DB:  ", await uploadResponse.json());
        return;
      }

      const data = await uploadResponse.json();

      if (data.usage_error) {
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
    setFiles([uploads[idx]]); // must be an array
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
        {tabSelection === "Analyze New Files" ? (
          <FileDragDrop // TODO figure out how to notify user if they attempt to upload existing recording
            handleFileChange={(files) => setFiles(Object.values(files))}
            dropZoneText={dropZoneText}
            fileSelection={files.length > 0 ? files.map(({ name }) => name).join(", ") : "No files selected"}
          />
        ) : (
          <DropDownContainer>
            <DropDownWidget
              options={formattedUploads}
              label="Select Recording"
              reset={files.length === 0}
              handleSelection={handleDropDownSelect}
            />
          </DropDownContainer>
        )}
        <AnalysisParamForm
          errorMessages={paramErrors}
          inputVals={analysisParams}
          checkedParams={checkedParams}
          setCheckedParams={updateCheckParams}
          paramErrors={paramErrors}
          setParamErrors={setParamErrors}
          setAnalysisParams={setAnalysisParams}
          analysisParams={analysisParams}
        />
        <ButtonContainer>
          {uploadSuccess ? <SuccessText>Upload Successful!</SuccessText> : null}
          <ButtonWidget
            width="135px"
            height="45px"
            position="relative"
            borderRadius="3px"
            label="Reset"
            clickFn={resetState}
          />
          <ButtonWidget
            width="135px"
            height="45px"
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
