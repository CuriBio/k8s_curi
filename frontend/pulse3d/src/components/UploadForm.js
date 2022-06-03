import styled from "styled-components";
import { useState, useEffect } from "react";

import FileDragDrop from "./FileDragDrop";
import AnalysisParamForm from "./AnalysisParamForm";
import { useWorker } from "@/components/hooks/useWorker";

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

export default function UploadForm() {
  const [state, setState] = useState({});
  const { error, result } = useWorker(state);

  const [file, setFile] = useState();
  // Tanner (6/2/22): there's probably a better way to do this without using a hook for the file name since file is already stored
  const [fileName, setFileName] = useState();

  const [analysisParams, setAnalysisParams] = useState({});

  useEffect(() => {
    // defaults to undefined when webworker state resets
    console.log("$$$ result:", result);
    if (result && result.status === 200) {
      if (state.endpoint === "/uploads") {
        setState({
          method: "post",
          presignedUrl: "TODO",
          body: "TODO",
        });
      } else if (state.presignedUrl) {
        // TODO: tell user that the upload was successful
      }
    }
  }, [result]);

  useEffect(() => {
    console.log("$$$:", error);
    // defaults to undefined when webworker state resets
    if (error) {
      // TODO: handle the error
    }
  }, [error]);

  const handleFileChange = (file) => {
    console.log(file);
    setFile(file);
    setFileName(file.name);
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
      filename: fileName,
      md5s: "TODO",
    };
    setState({
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
          fileSelection={fileName}
        />
        <AnalysisParamForm updateAnalysisParams={updateAnalysisParams} />
        <button style={buttonStyle} type="submit" onClick={handleUpload}>
          Submit
        </button>
      </Uploads>
    </Container>
  );
}
