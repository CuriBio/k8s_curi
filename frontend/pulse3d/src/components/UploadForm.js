import styled from "styled-components";
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
  border-radius: 20px;
  background-color: var(--light-gray);
`;

const dropZoneText = "Click to upload, or drop .h5/.zip file here";

export default function UploadForm() {
  return (
    <Container>
      <Uploads>
        <FileDragDrop dropZoneText={dropZoneText} />
        <AnalysisParamForm />
        {/* SubmitButton */}
      </Uploads>
    </Container>
  );
}
