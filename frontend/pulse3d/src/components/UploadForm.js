import styled from "styled-components";
import { useEffect, useState, useContext, useRef } from "react";

import AnalysisParamForm from "./AnalysisParamForm";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import FileDragDrop from "./FileDragDrop";
import { WorkerContext } from "@/components/WorkerWrapper";

const Container = styled.div`
  width: 100%;
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
  const [analysisParams, setAnalysisParams] = useState({
    twitchWidths: null,
    startTime: null,
    endTime: null,
  });

  useEffect(() => {
    // defaults to undefined when webworker state resets
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
    setFile(file);
  };

  const updateAnalysisParams = (newParams) => {
    let updatedParams = { ...analysisParams, ...newParams };

    try {
      updatedParams.twitchWidths = JSON.parse(updatedParams.twitchWidths);
      // TODO also assert that it's a list and it contains numbers
    } catch {
      // TODO display error message
      console.log(`Invalid twitchWidths array: ${updatedParams.twitchWidths}`);
    }

    console.log(JSON.stringify(updatedParams));
    setAnalysisParams(updatedParams);
  };

  const handleUpload = async () => {
    if (!file.name) {
      console.log("No file selected");
      // TODO: tell the user no file is selected
      return;
    }

    // TODO: if there are error messages, tell user to fix issues, then return

    console.log("uploading...");

    setReqParams({ file, type: "uploadFile" });
  };

  return (
    <Container>
      <Uploads>
        <FileDragDrop
          handleFileChange={handleFileChange}
          dropZoneText={dropZoneText}
          fileSelection={file.name}
        />
        <AnalysisParamForm updateAnalysisParams={updateAnalysisParams} />
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
