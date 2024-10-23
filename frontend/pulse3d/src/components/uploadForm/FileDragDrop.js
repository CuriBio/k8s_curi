import styled from "styled-components";
import { FileUploader } from "react-drag-drop-files";
import { useEffect } from "react";

const Container = styled.div`
  top: 28px;
  height: 170px;
  width: 70%;
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
  fileTypes,
  multiple = true,
}) {
  useEffect(() => {
    if (resetDragDrop) {
      setResetDragDrop(false);
    }
  }, [resetDragDrop]);

  const numFilesSelected = fileSelection?.length || 0;
  const numFilesLabel = (() => {
    if (numFilesSelected === 0) {
      return multiple ? "No files selected" : "No file selected";
    }
    if (numFilesSelected === 1) {
      return multiple ? "1 file selected" : "Selected file";
    }
    return `${numFilesSelected} files selected`;
  })();
  const fileSelectionListText = `[ ${(fileSelection || []).map(({ name }) => name).join(", ")} ]`;

  return (
    <Container style={containerStyle}>
      {!resetDragDrop && (
        <FileUploader
          hoverTitle=" "
          handleChange={handleFileChange}
          name="file"
          types={fileTypes}
          multiple={multiple}
        >
          <DropZone style={dropZoneStyle}>
            {dropZoneText}
            <br />
            <FileSelectionLabel>{`${numFilesLabel}: ${fileSelectionListText}`}</FileSelectionLabel>
          </DropZone>
        </FileUploader>
      )}
    </Container>
  );
}
