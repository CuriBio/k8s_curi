import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import SortIcon from "@mui/icons-material/Sort";
import { useState, useEffect } from "react";
import styled from "styled-components";

const ResizeDiv = styled.div`
  display: flex;
  align-items: center;
  &:hover {
    cursor: url("./drag-horizontal.png");
  }
`;
const Container = styled.div`
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;
const FilterInput = styled.input`
  width: 80%;
  padding: 5px 10px;
  margin-right: 5px;
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
  setSortColumn,
  sortColumn,
}) {
  const [input, setInput] = useState("");
  const [initialX, setInitialX] = useState();
  const [order, setOrder] = useState("");

  useEffect(() => {
    setOrder(sortColumn !== columnName ? "" : "asc");
  }, [sortColumn]);

  useEffect(() => {
    if (filterColumn !== columnName) {
      setInput("");
    }
  }, [filterColumn]);

  useEffect(() => {
    setFilterString(input);
  }, [input]);

  // useEffect(() => {
  //   console.log("X: ", initialX);
  // }, [initialX]);

  // useEffect(() => {
  //   if (title == "Recording Name") console.log("USE EFF: ", width);
  // }, [width]);

  const updateWidth = (e) => {
    console.log(e);
    const difference = parseInt(e.clientX - initialX);
    const newWidth = parseInt(width) + difference;
    const newNeighborWidth = parseInt(rightWidth) - difference;
    // console.log("-------------------------");
    // console.log("CLIENTX: ", e.clientX, initialX);
    // console.log("DIFF: ", difference);
    // console.log("WIDTH: ", width);
    // console.log("NEW WIDTH: ", newWidth);
    // console.log("NEIGHBOR: ", newNeighborWidth);

    // // size the columns in steps
    // if (Math.abs(difference) < 3 || newWidth < 9 || newNeighborWidth < 9) {
    //   return;
    // }

    setSelfWidth(`${newWidth}%`);
    setRightNeighbor(`${newNeighborWidth}%`);
    setInitialX(e.clientX);
  };

  return (
    <Container>
      <FilterInput
        autocomplete="off"
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
      {columnName !== order ? (
        <SortIcon
          onClick={() => {
            setOrder("asc");
            setSortColumn(columnName);
          }}
          style={{ color: "gray" }}
        />
      ) : (
        <SortIcon
          onClick={() => {
            setOrder(order === "asc" ? "desc" : "asc");
          }}
          style={{ transform: order === "desc" && "rotate(180deg)" }}
        />
      )}
      {!last && (
        <ResizeDiv
          onDragStart={(e) => {
            setInitialX(e.clientX);
          }}
          onDrag={(e) => {
            updateWidth(e);
          }}
          onClick={(e) => {
            e.stopPropagation();
          }}
          draggable
        >
          <DragIndicatorIcon />
        </ResizeDiv>
      )}
    </Container>
  );
}
