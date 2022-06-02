import styled from "styled-components";
import { useState } from "react";

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

  useEffect(() => {
    // defaults to undefined when webworker state resets
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
    // defaults to undefined when webworker state resets
    if (error) {
      // TODO: handle the error
    }
  }, [error]);

  const handleChange = (file) => {
    console.log(file);
    setFile(file);
    setFileName(file.name);
  };

  const getPresignedUploadUrl = () => {
    if (!file) {
      // TODO: tell the user no file is selected
      return;
    }

    uploadData = {
      filename: fileName,
      md5s: "TODO",
      customer_id: "TODO",
    };
    setState({
      method: "post",
      endpoint: "/uploads",
      body: uploadData,
    });
  };

  return (
    <Container>
      <Uploads>
        <FileDragDrop handleChange={handleChange} dropZoneText={dropZoneText} fileSelection={fileName} />
        <AnalysisParamForm />
        <button style={buttonStyle} type="submit" onClick={getPresignedUploadUrl}>
          Submit
        </button>
      </Uploads>
    </Container>
  );
}
