import styled from "styled-components";
import { useState, useEffect } from "react";

import FileDragDrop from "./FileDragDrop";
import AnalysisParamForm from "./AnalysisParamForm";

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

const buttonStyle = {
  top: "82%",
  left: "73%",
  width: "110px",
  height: "30px",
  borderRadius: "3px",
};

export default function UploadForm({ makeRequest, response, error }) {
  const [file, setFile] = useState({});
  const [analysisParams, setAnalysisParams] = useState({});

  useEffect(() => {
    // defaults to undefined when webworker state resets
    console.log("$$$ response:", response);
    if (response) {
      if (response.endpoint === "/uploads") {
        makeRequest({
          method: "post",
          presignedUrl: "TODO",
          body: "TODO",
        });
      } else if (response.presignedUrl) {
        // TODO: tell user that the upload was successful
      }
    }
  }, [response]);

  useEffect(() => {
    console.log("$$$ error:", error);
    // defaults to undefined when webworker state resets
    if (error) {
      // TODO: handle the error
    }
  }, [error]);

  const handleFileChange = (file) => {
    console.log("file", file);
    console.log("file", file);
    setFile(file);
  };

  const updateAnalysisParams = (newParams) => {
    let updatedParams = { ...analysisParams, ...newParams };

    try {
      updatedParams.twitchWidths = JSON.parse(updatedParams.twitchWidths);
    } catch {
      // TODO display error message
      console.log(`Invalid twitchWidths array: ${updatedParams.twitchWidths}`);
    }

    console.log(JSON.stringify(updatedParams));
    setAnalysisParams(updatedParams);
  };

  const handleUpload = () => {
    if (!file) {
      console.log("No file selected");
      // TODO: tell the user no file is selected
      return;
    }

    // TODO: if there are error messages, tell user to fix issues, then return

    console.log("uploading...");

    const uploadData = {
      filename: file.name,
      md5s: "TODO",
    };
    makeRequest({
      method: "post",
      endpoint: "/uploads",
      body: uploadData,
      subdomain: "pulse3d",
    });
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
        <button style={buttonStyle} type="submit" onClick={handleUpload}>
          Submit
        </button>
      </Uploads>
    </Container>
  );
}
