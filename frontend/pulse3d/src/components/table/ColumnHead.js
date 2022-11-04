import DragHandleIcon from "@mui/icons-material/DragHandle";
import SortByAlphaIcon from "@mui/icons-material/SortByAlpha";
import { useState, useEffect } from "react";
import styled from "styled-components";
const ResizeDiv = styled.div`
  transform: rotate(90deg);
`;
const Container = styled.div`
  width: 100%;
  display: flex;
  justify-content: space-between;
`;
const FilterInput = styled.input`
  width: 50%;
`;
export default function ColumnHead({
  title,
  setFilterString,
  setFilterColumn,
  columnName,
  width,
  setSelfWidth,
  setRightNeighbor,
  rightWidth,
  last,
}) {
  const [input, setInput] = useState("");
  const [initialX, setInitialX] = useState();
  useEffect(() => {
    setFilterString(input);
    setFilterColumn(columnName);
  }, [input]);

  const updateWidth = (e) => {
    const difference = e.clientX - initialX;
    const newWidth = parseInt(width) + difference;
    const newNeighborWidth = parseInt(rightWidth) - difference;
    //prevent user from making columns to small
    if (newWidth < 150 || newNeighborWidth < 150) {
      return;
    }
    setSelfWidth(`${newWidth}px`);
    setRightNeighbor(`${newNeighborWidth}px`);
    setInitialX(e.clientX);
  };
  return (
    <Container>
      <FilterInput
        type="text"
        placeholder={title}
        onClick={(e) => {
          e.stopPropagation();
        }}
        onChange={(e) => {
          setInput(e.target.value);
        }}
      />

      <SortByAlphaIcon />
      {
        <ResizeDiv
          onMouseDown={(e) => {
            setInitialX(e.clientX);
          }}
          onDrag={(e) => {
            updateWidth(e);
          }}
          onClick={(e) => {
            e.stopPropagation();
          }}
          draggable={true}
        >
          <DragHandleIcon />
        </ResizeDiv>
      }
    </Container>
  );
}
