import { useEffect, useState } from "react";
import styled from "styled-components";
const InputsContainer = styled.div`
  width: 100%;
  display: flex;
  justify-content: space-evenly;
`;
export default function FilterHeader(props) {
  const [input, setInput] = useState("");
  const [columnName, setColumnName] = useState("");

  //when collumn changes then reset all inputs
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

  //when input changes update the filterstring
  useEffect(() => {
    props.setFilterString(input);
  }, [input]);

  const searchFields = props.columns.map((column, idx) => {
    if (!props.loading) {
      return column === "" ? (
        <input
          disabled
          key={idx}
          className="searchBox"
          type="text"
          onChange={(e) => {
            setInput(e.target.value);
            setColumnName(column);
          }}
          style={{ backgroundColor: "var(--dark-blue)", border: "none" }}
        />
      ) : (
        <input
          key={idx}
          id={column}
          className="searchBox"
          type="text"
          placeholder={`Search ${column}`}
          onChange={(e) => {
            setInput(e.target.value);
            setColumnName(column);
          }}
        />
      );
    }
  });
  return <InputsContainer>{searchFields}</InputsContainer>;
}
