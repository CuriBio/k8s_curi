import styled from "styled-components";
import { useEffect, useState, useContext, useRef } from "react";

import AnalysisParamForm from "./AnalysisParamForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import FileDragDrop from "./FileDragDrop";
import { WorkerContext } from "@/components/WorkerWrapper";
import { isArrayOfNumbers } from "@/utils/generic";

const Container = styled.div`
  width: 80%;
  height: inherit;
  justify-content: center;
  position: relative;
  padding-top: 5%;
  padding-left: 5%;
`;

const Uploads = styled.div`
  width: 90%;
  height: 90%;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 15px;
  background-color: var(--light-gray);
`;

const dropZoneText = "Click here or drop .h5/.zip file to upload";

const buttonStyle = {};

export default function UploadForm() {
  const { setReqParams, response, error } = useContext(WorkerContext); // global app state
  const newReq = useRef(false); // this check prevents old response from being used on mount when switching between pages

  const [file, setFile] = useState({});

  const [analysisParams, setAnalysisParams] = useState({});
  const [paramErrors, setParamErrors] = useState({});

  useEffect(() => {
    // defaults to undefined when webworker state resets
    console.log("$$$ response:", response);
    if (response && newReq.current) {
      if (response.type === "uploadFile") {
        setReqParams({
          method: "post",
          endpoint: "jobs",
          type: "startAnalysis",
          body: {
            upload_id: response.uploadId,
            twitch_widths: analysisParams.twitchWidths,
            start_time: analysisParams.startTime,
            end_time: analysisParams.endTime,
          },
        });
      } else if (response.type === "startAnalysis") {
        console.log("Analysis in progress!");
        // TODO: tell user that the upload was successful
      }
    }

    newReq.current = true; // this check prevents old response from being used on mount when switching between pages
  }, [response]);

  useEffect(() => {
    // defaults to undefined when webworker state resets
    if (error && newReq.current) {
      console.log("$$$ error:", error);
      // TODO: handle the error
    }
  }, [error]);

  const handleFileChange = (file) => {
    console.log("file", file);
    setFile(file);
  };

  const handleUpload = async () => {
    if (!file.name) {
      console.log("No file selected");
      // TODO: tell the user no file is selected
      return;
    }
    if (true /* TODO check paramErrors for any error messages */) {
      console.log("Fix invalid params before uploading");
      // TODO: tell user to fix issues
      return;
    }

    console.log("uploading...");

    setReqParams({ file, type: "uploadFile" });
  };

  const updateParams = (newParams) => {
    const updatedParams = { ...analysisParams, ...newParams };
    console.log("updateParams new params:", JSON.stringify(updatedParams));

    if (newParams.twitchWidths !== undefined) {
      validateTwitchWidths(updatedParams);
    }
    if (newParams.startTime !== undefined || newParams.endTime !== undefined) {
      // need to validate start and end time together
      validateWindowBounds(updatedParams);
    }

    setAnalysisParams(updatedParams);
    console.log("updateParams formatted params:", JSON.stringify(updatedParams));
  };

  const validateTwitchWidths = (updatedParams) => {
    const newValue = updatedParams.twitchWidths;
    console.log("validateTwitchWidths:", newValue);
    let formattedTwitchWidths;
    if (newValue === null || newValue === "") {
      formattedTwitchWidths = null;
    } else {
      let twitchWidthArr;
      // make sure it's a valid list
      try {
        twitchWidthArr = JSON.parse(`[${newValue}]`);
      } catch (e) {
        console.log(`Invalid twitchWidths: ${newValue}, ${e}`);
        setParamErrors({ ...paramErrors, twitchWidths: "Must be comma-separated, positive numbers" });
        return;
      }
      // make sure it's an array of positive numbers
      if (isArrayOfNumbers(twitchWidthArr, true)) {
        formattedTwitchWidths = Array.from(new Set(twitchWidthArr));
        console.log("formattedTwitchWidths:", formattedTwitchWidths);
      } else {
        console.log(`Invalid twitchWidths: ${newValue}`);
        setParamErrors({ ...paramErrors, twitchWidths: "Must be comma-separated, positive numbers" });
        return;
      }
    }
    console.log("VALID TW");
    setParamErrors({ ...paramErrors, twitchWidths: "" });
    updatedParams.twitchWidths = formattedTwitchWidths;
  };

  const validateWindowBounds = (updatedParams) => {
    const { startTime, endTime } = updatedParams;
    const updatedParamErrors = { ...paramErrors };

    for (const [boundName, boundValueStr] of Object.entries({ startTime, endTime })) {
      let error = "";
      if (boundValueStr) {
        const boundValue = +boundValueStr;
        updatedParams[boundName] = boundValue;
        if (boundValue < 0) {
          error = "Must be a non-negative number";
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
      updatedParamErrors.endTime = "Must be greater than Start Time";
    }
    setParamErrors(updatedParamErrors);
  };

  return (
    <Container>
      <Uploads>
        <FileDragDrop
          handleFileChange={handleFileChange}
          dropZoneText={dropZoneText}
          fileSelection={file.name}
        />
        <AnalysisParamForm errorMessages={paramErrors} updateParams={updateParams} />
        <ButtonWidget
          top={"20%"}
          left={"80%"}
          width={"115px"}
          height={"30px"}
          position={"relative"}
          borderRadius={"3px"}
          label="Submit"
          clickFn={handleUpload}
        />
      </Uploads>
    </Container>
  );
}
