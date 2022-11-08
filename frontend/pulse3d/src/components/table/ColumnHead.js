import DragHandleIcon from "@mui/icons-material/DragHandle";
import EjectIcon from "@mui/icons-material/Eject";
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
  width: 80%;
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
  filterColumn,
  setSortColumns,
  sortColumn,
}) {
  const [input, setInput] = useState("");
  const [initialX, setInitialX] = useState();
  const [order, setOrder] = useState("");
  useEffect(() => {
    if (sortColumn !== columnName) {
      setOrder("");
    }
  }, [sortColumn]);
  useEffect(() => {
    if (filterColumn !== columnName) {
      setInput("");
    }
  }, [filterColumn]);
  useEffect(() => {
    setFilterString(input);
  }, [input]);

  const updateWidth = (e) => {
    const difference = parseInt((e.clientX - initialX) / 10);
    const newWidth = parseInt(width) + difference;
    const newNeighborWidth = parseInt(rightWidth) - difference;
    //prevent user from making columns to small
    // if (newWidth < 150 || newNeighborWidth < 150) {
    //   return;
    // }
    //steps
    if (Math.abs(difference) < 3 || newWidth < 9 || newNeighborWidth < 9) {
      return;
    }
    setSelfWidth(`${newWidth}%`);
    setRightNeighbor(`${newNeighborWidth}%`);
    setInitialX(e.clientX);
  };
  return (
    <Container>
      <FilterInput
        value={input}
        type="text"
        placeholder={title}
        onChange={(e) => {
          setInput(e.target.value);
          setFilterColumn(columnName);
        }}
        onClick={(e) => {
          e.stopPropagation();
        }}
      />
      {order === "" ? (
        <EjectIcon
          onClick={() => {
            setOrder("asc");
            setSortColumns(columnName);
          }}
          style={{ color: "gray" }}
        />
      ) : null}
      {order === "asc" && (
        <EjectIcon
          onClick={() => {
            setOrder("desc");
          }}
        />
      )}
      {order === "desc" && (
        <EjectIcon
          onClick={() => {
            setOrder("asc");
          }}
          style={{ transform: "rotate(180deg)" }}
        />
      )}
      {!last && (
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
      )}
    </Container>
  );
}
