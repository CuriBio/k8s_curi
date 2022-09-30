import { useEffect, useState } from "react";
import styled from "styled-components";
const Test = styled.div`
  width: 100%;
  display: flex;
  justify-content: space-around;
`;
export default function FilterHeader(props) {
  const [input, setInput] = useState("");
  const [columnName, setColumnName] = useState("");
  useEffect(() => {
    props.setFilterColumn(columnName);
    Array.from(document.getElementsByClassName("searchBox")).forEach(
      (input) => {
        if (input.id !== columnName) {
          input.value = "";
        }
      }
    );
  }, [columnName]);
  useEffect(() => {
    props.setFilterString(input);
  }, [input]);
  const searchFields = props.columns.map((column, idx) =>
    column !== "" ? (
      <input
        key={idx}
        id={column}
        className="searchBox"
        type="text"
        placeholder={column}
        onChange={(e) => {
          setInput(e.target.value);
          setColumnName(column);
        }}
      />
    ) : (
      <input
        disabled
        key={idx}
        className="searchBox"
        type="text"
        placeholder={column}
        onChange={(e) => {
          setInput(e.target.value);
          setColumnName(column);
        }}
        style={{ backgroundColor: "var(--dark-blue)", border: "none" }}
      />
    )
  );
  return <Test>{searchFields}</Test>;
}
