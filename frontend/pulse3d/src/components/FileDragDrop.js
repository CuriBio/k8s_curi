import styled from "styled-components";
import React, { useState } from "react";
import { FileUploader } from "react-drag-drop-files";

const fileTypes = ["h5", "zip"];

const Container = styled.div`
  left: 5%;
  top: 5%;
  height: 15%;
  width: 90%;
  position: relative;
`;

const DropZone = styled.div`
  width: 100%;
  height: 100%;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 20px;
  background-color: white;
  display: flex;
  justify-content: center;
  align-content: center;
  flex-direction: column;
  text-align: center;
`;

export default function FileDragDrop({
  dropZoneText = "Drop Here",
  containerStyle = {},
  dropZoneStyle = {},
}) {
  const [file, setFile] = useState(null);
  const handleChange = (file) => {
    setFile(file);
  };
  return (
    <Container style={containerStyle}>
      <FileUploader handleChange={handleChange} name="file" types={fileTypes}>
        <DropZone style={dropZoneStyle}>{dropZoneText}</DropZone>
      </FileUploader>
    </Container>
  );
}
