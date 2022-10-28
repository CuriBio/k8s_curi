import { useState } from "react";
import styled from "styled-components";
const ResizeDiv = styled.div`
  width: 5px;
  height: 100%;
  min-width: 2px;
  min-heigth: 1px;
  background-color: black;
  cursor: col-resize;
  border-radius: 3px;
`;
const RowCell = styled.div`
  height: 30px;
  display: flex;
  align-items: center;
  padding-left: 20px;
`;
export default function ResizableColumn({ content, width, setSelfWidth, setRightNeighbor, rightWidth }) {
  const [initialX, setInitialX] = useState();

  const updateWidth = (e) => {
    const difference = e.clientX - initialX;
    const newWidth = parseInt(width) + difference;
    if (newWidth < 100) {
      return;
    }
    setSelfWidth(`${newWidth}px`);
    setRightNeighbor(`${parseInt(rightWidth) - difference}px`);
    setInitialX(e.clientX);
  };

  return (
    <>
      <RowCell style={{ width: `${width}px` }}>{content}</RowCell>
      <ResizeDiv
        onMouseDown={(e) => {
          setInitialX(e.clientX);
        }}
        onDrag={(e) => {
          updateWidth(e);
        }}
      />
    </>
  );
}
