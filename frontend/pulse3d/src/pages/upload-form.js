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

const Container = styled.div`
  width: 70%;
  justify-content: center;
  position: relative;
  padding-top: 3%;
  padding-left: 7%;
  padding-bottom: 3%;
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

const getDefaultAnalysisParams = () => {
  return {
    yAxisNormalization: false,
    baseToPeak: "",
    peakToBase: "",
    maxY: "",
    prominenceFactor: "",
    widthFactor: "",
    twitchWidths: "",
    startTime: "",
    endTime: "",
    selectedPulse3dVersion: "", // Tanner (9/15/22): The pulse3d version technically isn't a param, so could move this value to its own state if needed
  };
};

export default function UploadForm() {
  const { query } = useRouter();
  const { uploads, pulse3dVersions } = useContext(UploadsContext);
  const [files, setFiles] = useState([]);
  const [formattedUploads, setFormattedUploads] = useState([]);
  const [isButtonDisabled, setIsButtonDisabled] = useState(true);
  const [paramErrors, setParamErrors] = useState({});
  const [inProgress, setInProgress] = useState(false);
  const [modalButtons, setModalButtons] = useState(["Close"]);
  const [failedUploadsMsg, setFailedUploadsMsg] = useState([defaultUploadErrorLabel]);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [checkedParams, setCheckedParams] = useState(false);
  const [tabSelection, setTabSelection] = useState(query.id);
  const [modalState, setModalState] = useState(false);
  const [analysisParams, setAnalysisParams] = useState(getDefaultAnalysisParams());

  // TODO remove this value once entire advanced analysis section is under a single checkbox
  const [resetDropDown, setResetDropDown] = useState(0);

  useEffect(() => {
    // checks if error value exists, no file is selected, or upload is in progress
    const checkConditions =
      !Object.values(paramErrors).every((val) => val.length === 0) ||
      !((files.length > 0 && files[0] instanceof File) || uploads.includes(files[0])) ||
      inProgress;

    setIsButtonDisabled(checkConditions);
  }, [paramErrors, files, inProgress]);

  useEffect(() => {
    // resets upload status when user makes changes
    if (
      (files.length > 0 && files[0] instanceof File) ||
      Object.values(analysisParams).some((val) => val.length > 0)
    ) {
      setUploadSuccess(false);
    }
  }, [files, analysisParams]);

  useEffect(() => {
    // reset all params if the user switches between the "re-analyze" and "new upload" versions of this page
    setTabSelection(query.id);
    resetState();
  }, [query]);

  useEffect(() => {
    const uploadFilenames = uploads.map((upload) => upload.filename).filter((name) => name);

    setFormattedUploads([...uploadFilenames]);
  }, [uploads]);

  const resetState = () => {
    setFiles([]);
    setAnalysisParams(getDefaultAnalysisParams());
    setFailedUploadsMsg([defaultUploadErrorLabel]);
    setModalButtons(["Close"]);
    setCheckedParams(false);
    setParamErrors({});
    // Tanner (9/13/22): this is a really hacky way of triggering this since the value must actually change, but it will be unnecessary once the single checkbox is added
    setResetDropDown(resetDropDown + 1);
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
        yAxisNormalization,
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
      } = analysisParams;

      const requestBody = {
        upload_id: uploadId,
        normalize_y_axis: yAxisNormalization,
        baseline_widths_to_use: formatTupleParams(baseToPeak, peakToBase),
        prominence_factors: formatTupleParams(prominenceFactorPeaks, prominenceFactorValleys),
        width_factors: formatTupleParams(widthFactorPeaks, widthFactorValleys),
        twitch_widths: twitchWidths === "" ? null : twitchWidths,
        start_time: startTime === "" ? null : startTime,
        end_time: endTime === "" ? null : endTime,
        // pulse3d versions are currently sorted in desc order, so pick the first (latest) version as the default
        version: selectedPulse3dVersion === "" ? pulse3dVersions[0] : selectedPulse3dVersion,
      };
      if (requestBody.version !== "0.24.6") {
        // Tanner (9/15/21): at the time of writing this, 0.24.6 is the only available pulse3D version that does not support the max_y param
        requestBody.max_y = maxY === "" ? null : maxY;
      }

      const jobResponse = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs`, {
        method: "POST",
        body: JSON.stringify(requestBody),
      });
      if (jobResponse.status !== 200) {
        failedUploadsMsg.push(filename);
        console.log("ERROR posting new job: ", await jobResponse.json());
      }
    } catch (e) {
      failedUploadsMsg.push(filename);
      console.log("ERROR posting new job");
    }
  };

  const submitNewAnalysis = async () => {
    await checkForMultiRecZips();
    resetState();
  };

  const checkForMultiRecZips = async () => {
    var JSZip = require("jszip");

    if (tabSelection === "1") {
      const asyncFilter = async (arr, predicate) =>
        Promise.all(arr.map(predicate)).then((results) => arr.filter((_v, index) => results[index]));

      const badZipfiles = await asyncFilter(files, async (file) => {
        try {
          const zip = new JSZip();
          const { files } = await zip.loadAsync(file);

          const dirs = Object.values(files).filter(({ dir }) => dir);
          const onlyOneRec = dirs.length === 0 || dirs.length === 1;

          const numFilesInRecording = Object.keys(files).filter(
            (filename) => filename.includes(".h5") && !filename.includes("__MACOSX")
          ).length;

          // Beta 1 recordings will contain 24 files, Beta 2 and V1 recordings will contain 48
          const recordingContainsValidNumFiles = numFilesInRecording === 24 || numFilesInRecording === 48;

          return !onlyOneRec || !recordingContainsValidNumFiles;
        } catch (e) {
          console.log(`ERROR unable to read zip file: ${file.name} ${e}`);
          failedUploadsMsg.push(file.name);
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
          upload_type: "mantarray",
        }),
      });

      // break flow if initial request returns error status code
      if (uploadResponse.status !== 200) {
        failedUploadsMsg.push(filename);
        console.log("ERROR uploading file metadata to DB:  ", await uploadResponse.json());
        return;
      }

      const data = await uploadResponse.json();
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
      failedUploadsMsg.push(filename);
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
  };

  return (
    <Container>
      <Uploads>
        <Header>Run Analysis</Header>
        {tabSelection === "1" ? (
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
          setCheckedParams={setCheckedParams}
          paramErrors={paramErrors}
          setParamErrors={setParamErrors}
          setAnalysisParams={setAnalysisParams}
          analysisParams={analysisParams}
          pulse3dVersions={pulse3dVersions}
          resetDropDown={resetDropDown}
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
    </Container>
  );
}

UploadForm.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
