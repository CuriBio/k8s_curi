import styled from "styled-components";
import { FileUploader } from "react-drag-drop-files";

const fileTypes = ["h5", "zip"];

const Container = styled.div`
  left: 5%;
  top: 5%;
  height: 20%;
  width: 90%;
  position: relative;
  font-size: 22px;
`;

const DropZone = styled.div`
  width: 100%;
  height: 100%;
  border: 2px dashed black;
  border-radius: 5px;
  background-color: var(--med-gray);
  display: flex;
  justify-content: center;
  align-content: center;
  flex-direction: column;
  text-align: center;
  &:hover {
    background-color: var(--light-gray);
    cursor: pointer;
  }
`;

export default function FileDragDrop({
  handleFileChange,
  fileSelection,
  dropZoneText = "Drop Here",
  containerStyle = {},
  dropZoneStyle = {},
}) {
  return (
    <Container style={containerStyle}>
      <FileUploader
        hoverTitle=" "
        handleChange={handleFileChange}
        name="file"
        types={fileTypes}
        multiple={false}
      >
        <DropZone style={dropZoneStyle}>
          {dropZoneText}
          <br />({fileSelection || "No file selected"})
        </DropZone>
      </FileUploader>
    </Container>
  );
}
