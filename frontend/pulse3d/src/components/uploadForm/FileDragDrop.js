import styled from "styled-components";
import { FileUploader } from "react-drag-drop-files";
import { useEffect } from "react";

const fileTypes = ["zip", "xlsx"];

const Container = styled.div`
  left: 5%;
  top: 28px;
  height: 170px;
  width: 90%;
  position: relative;
  font-size: 24px;
  overflow: scroll;
  border: 2px dashed black;
  border-radius: 5px;
  background-color: var(--med-gray);
  cursor: pointer;
  font-weight: bold;
  &:hover {
    background-color: var(--light-gray);
  }
  &::-webkit-scrollbar {
    display: none;
  }
`;

const DropZone = styled.div`
  display: flex;
  justify-content: center;
  align-content: center;
  flex-direction: column;
  text-align: center;
  line-height: 2;
  cursor: pointer;
  height: 170px;
`;

const FileSelectionLabel = styled.div`
  font-style: italic;
  font-size: 18px;
`;

export default function FileDragDrop({
  handleFileChange,
  fileSelection,
  dropZoneText = "Drop Here",
  containerStyle = {},
  dropZoneStyle = {},
  setResetDragDrop,
  resetDragDrop,
}) {
  useEffect(() => {
    if (resetDragDrop) setResetDragDrop(false);
  }, [resetDragDrop]);

  return (
    <Container style={containerStyle}>
      {!resetDragDrop && (
        <FileUploader
          hoverTitle=" "
          handleChange={handleFileChange}
          name="file"
          types={fileTypes}
          multiple={true}
        >
          <DropZone style={dropZoneStyle}>
            {dropZoneText}
            <br />
            <FileSelectionLabel>[ {fileSelection || "No file selected"} ]</FileSelectionLabel>
          </DropZone>
        </FileUploader>
      )}
    </Container>
  );
}
