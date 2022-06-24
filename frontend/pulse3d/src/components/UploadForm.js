import styled from "styled-components";
import { useEffect, useState } from "react";
import AnalysisParamForm from "./AnalysisParamForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import FileDragDrop from "./FileDragDrop";
import SparkMD5 from "spark-md5";
import { hexToBase64, isArrayOfNumbers } from "../utils/generic";

const Container = styled.div`
  width: 100%;
  height: inherit;
  justify-content: center;
  position: relative;
  padding-top: 5%;
  padding-left: 15%;
`;

const Uploads = styled.div`
  width: 70%;
  height: 70%;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 15px;
  background-color: white;
`;

const ButtonContainer = styled.div`
  position: relative;
  top: 16%;
  justify-content: flex-end;
  display: flex;
  padding-right: 12%;
  align-items: center;
`;
const ErrorText = styled.span`
  color: red;
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
`;

const SuccessText = styled.span`
  color: green;
  font-style: italic;
  font-size: 15px;
  padding-right: 10px;
`;
const dropZoneText = "Click here or drop .h5/.zip file to upload";

export default function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState({});
  const [isButtonDisabled, setIsButtonDisabled] = useState(true);
  const [paramErrors, setParamErrors] = useState({});
  const [inProgress, setInProgress] = useState(false);
  const [uploadError, setUploadError] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [checked, setChecked] = useState(false);
  const [analysisParams, setAnalysisParams] = useState({
    twitchWidths: "",
    startTime: "",
    endTime: "",
  });

  useEffect(() => {
    // checks if error value exists, no file is selected, or upload is in progress
    const checkConditions =
      !Object.values(paramErrors).every((val) => val.length === 0) ||
      !(file instanceof File) ||
      inProgress;

    setIsButtonDisabled(checkConditions);
  }, [paramErrors, file, inProgress]);

  useEffect(() => {
    // resets state when upload status changes
    if (uploadError || uploadSuccess) {
      resetState();
    }
  }, [uploadError, uploadSuccess]);

  useEffect(() => {
    // resets upload status when user makes changes
    if (
      file instanceof File ||
      Object.values(analysisParams).some((val) => val.length > 0)
    ) {
      setUploadError(false);
      setUploadSuccess(false);
    }
  }, [file, analysisParams]);

  const resetState = () => {
    setFile(null);
    setAnalysisParams({
      twitchWidths: "",
      startTime: "",
      endTime: "",
    });

    setChecked(false);
    setParamErrors({});
  };

  const postNewJob = async (uploadId) => {
    const { twitchWidths, startTime, endTime } = analysisParams;
    const jobResponse = await fetch("http://localhost/jobs", {
      method: "POST",
      body: JSON.stringify({
        upload_id: uploadId,
        twitch_widths: twitchWidths === "" ? null : twitchWidths,
        start_time: startTime === "" ? null : startTime,
        end_time: endTime === "" ? null : endTime,
      }),
    });

    if (jobResponse.status !== 200) {
      console.log("ERROR posting new job: ", await jobResponse.json());
    }
  };

  const handleUpload = async () => {
    if (!file.name) {
      console.log("No file selected");
      // TODO: tell the user no file is selected
      return;
    }
    // update state to trigger in progress spinner over submit button
    setInProgress(true);

    let fileReader = new FileReader();
    fileReader.onload = async function (e) {
      if (file.size != e.target.result.byteLength) {
        console.log(
          "ERROR:</strong> Browser reported success but could not read the file until the end."
        );
        return;
      }

      let hash = SparkMD5.ArrayBuffer.hash(e.target.result);
      const uploadResponse = await fetch("http://localhost/uploads", {
        method: "POST",
        body: JSON.stringify({
          filename: file.name,
          md5s: hexToBase64(hash),
        }),
      });

      // break flow if initial request returns error status code
      if (uploadResponse.status !== 200) {
        setUploadError(true);
        setInProgress(false);
        console.log(
          "ERROR uploading file metadata to DB:  ",
          await uploadResponse.json()
        );
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

      // regardless of error or job status, set to false to show it has been processed
      setInProgress(false);

      if (uploadPostRes.status === 204) {
        // start job
        setUploadSuccess(true);
        await postNewJob(uploadId);
      } else {
        setUploadError(true);
        console.log(
          "ERROR uploading file to s3:  ",
          await uploadPostRes.json()
        );
      }
    };

    fileReader.onerror = function () {
      console.log(
        "ERROR: FileReader onerror was triggered, maybe the browser aborted due to high memory usage."
      );
      return;
    };

    fileReader.readAsArrayBuffer(file);
  };

  const updateParams = (newParams) => {
    const updatedParams = { ...analysisParams, ...newParams };

    if (newParams.twitchWidths !== undefined) {
      validateTwitchWidths(updatedParams);
    }
    if (newParams.startTime !== undefined || newParams.endTime !== undefined) {
      // need to validate start and end time together
      validateWindowBounds(updatedParams);
    }

    setAnalysisParams(updatedParams);
  };

  const validateTwitchWidths = (updatedParams) => {
    const newValue = updatedParams.twitchWidths;
    let formattedTwitchWidths;
    if (newValue === null || newValue === "") {
      formattedTwitchWidths = "";
    } else {
      let twitchWidthArr;
      // make sure it's a valid list
      try {
        twitchWidthArr = JSON.parse(`[${newValue}]`);
      } catch (e) {
        setParamErrors({
          ...paramErrors,
          twitchWidths: "*Must be comma-separated, positive numbers",
        });
        return;
      }
      // make sure it's an array of positive numbers
      if (isArrayOfNumbers(twitchWidthArr, true)) {
        formattedTwitchWidths = Array.from(new Set(twitchWidthArr));
        console.log("formattedTwitchWidths:", formattedTwitchWidths);
      } else {
        console.log(`Invalid twitchWidths: ${newValue}`);
        setParamErrors({
          ...paramErrors,
          twitchWidths: "*Must be comma-separated, positive numbers",
        });
        return;
      }
    }
    setParamErrors({ ...paramErrors, twitchWidths: "" });
    updatedParams.twitchWidths = formattedTwitchWidths;
  };

  const validateWindowBounds = (updatedParams) => {
    const { startTime, endTime } = updatedParams;
    const updatedParamErrors = { ...paramErrors };

    for (const [boundName, boundValueStr] of Object.entries({
      startTime,
      endTime,
    })) {
      let error = "";
      if (boundValueStr) {
        // checks if positive number, no other characters allowed
        const numRegEx = new RegExp("^([0-9]+(?:[.][0-9]*)?|.[0-9]+)$");
        if (!numRegEx.test(boundValueStr)) {
          error = "*Must be a non-negative number";
        } else {
          const boundValue = +boundValueStr;
          updatedParams[boundName] = boundValue;
        }
      }

      updatedParamErrors[boundName] = error;
    }

    if (
      !updatedParamErrors.startTime &&
      !updatedParamErrors.endTime &&
      updatedParams.startTime &&
      updatedParams.endTime &&
      updatedParams.startTime >= updatedParams.endTime
    ) {
      updatedParamErrors.endTime = "*Must be greater than Start Time";
    }
    setParamErrors(updatedParamErrors);
  };

  return (
    <Container>
      <Uploads>
        <FileDragDrop
          handleFileChange={(file) => {
            setFile(file);
          }}
          dropZoneText={dropZoneText}
          fileSelection={file ? file.name : null}
        />
        <AnalysisParamForm
          errorMessages={paramErrors}
          updateParams={updateParams}
          inputVals={analysisParams}
          checked={checked}
          setChecked={setChecked}
        />
        <ButtonContainer>
          {uploadError ? (
            <ErrorText>Error occurred! Try again.</ErrorText>
          ) : null}
          {uploadSuccess ? <SuccessText>Upload Successful!</SuccessText> : null}
          <ButtonWidget
            width={"135px"}
            height={"45px"}
            position={"relative"}
            borderRadius={"3px"}
            label="Reset"
            clickFn={resetState}
          />
          <ButtonWidget
            width={"135px"}
            height={"45px"}
            position={"relative"}
            borderRadius={"3px"}
            backgroundColor={
              isButtonDisabled ? "var(--dark-gray)" : "var(--dark-blue)"
            }
            disabled={isButtonDisabled}
            inProgress={inProgress}
            label="Submit"
            clickFn={handleUpload}
          />
        </ButtonContainer>
      </Uploads>
    </Container>
  );
}
