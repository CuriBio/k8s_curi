import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import SortIcon from "@mui/icons-material/Sort";
import { useState, useEffect } from "react";
import styled from "styled-components";

const ResizeDiv = styled.div`
  display: flex;
  cursor: col-resize;
  align-items: center;
`;

const GhostDiv = styled.div`
  height: 20px;
  width: 20px;
  position: relative;
  right: 20px;
  z-index: 2;
  cursor: col-resize;
`;

const Container = styled.div`
  width: 100%;
  display: flex;
  height: 70px;
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
    if (sortColumn !== columnName) {
      setOrder("");
    } else {
      setOrder("asc");
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
    // 50 is arbitrary here, 100 was too slow, it's an attempt to translate to percentage
    const difference = (e.clientX - initialX) / 50;
    const newWidth = parseFloat(+width + difference);
    const newNeighborWidth = parseFloat(+rightWidth - difference);

    // size the columns in steps
    if (Math.abs(difference) < 0.5 || newWidth < 10 || newNeighborWidth < 10) {
      return;
    }

    setSelfWidth(`${+newWidth.toFixed(2)}%`);
    setRightNeighbor(`${+newNeighborWidth.toFixed(2)}%`);
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
      {order == "" ? (
        <SortIcon
          onClick={() => {
            setOrder("asc");
            setSortColumn(columnName);
          }}
          style={{ color: "gray", fontSize: "20px", margin: "0 5px" }}
        />
      ) : (
        <SortIcon
          onClick={() => {
            setOrder(order === "asc" ? "desc" : "asc");
          }}
          style={{ transform: order === "desc" && "rotate(180deg)", margin: "0px 5px" }}
        />
      )}
      {!last && (
        <>
          <ResizeDiv>
            <DragIndicatorIcon />
          </ResizeDiv>
          <GhostDiv
            onMouseDown={(e) => {
              setInitialX(e.clientX);
            }}
            onDrag={(e) => {
              updateWidth(e);
            }}
            onClick={(e) => {
              e.stopPropagation();
            }}
            draggable
          />
        </>
      )}
    </Container>
  );
}
