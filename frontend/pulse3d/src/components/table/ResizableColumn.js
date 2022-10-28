import { useState } from "react";
import styled from "styled-components";
const ResizeRigth = styled.div`
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
export default function ReasizableColumn({ content, width, setSelfWidth, setRightNeighbor, rightWidth }) {
  const [initialX, setIntialx] = useState();

  const updateWidth = (e) => {
    const differnce = e.clientX - initialX;
    const newWidth = parseInt(width) + differnce;
    if (newWidth < 100) {
      return;
    }
    setSelfWidth(`${newWidth}px`);
    setRightNeighbor(`${parseInt(rightWidth) - differnce}px`);
    setIntialx(e.clientX);
  };

  return (
    <>
      <RowCell style={{ width: `${width}px` }}>{content}</RowCell>
      <ResizeRigth
        onMouseDown={(e) => {
          setIntialx(e.clientX);
        }}
        onDrag={(e) => {
          updateWidth(e);
        }}
      />
    </>
  );
}
