import styled from "styled-components";
import { useEffect, useState } from "react";
import CheckboxWidget from "@/components/basicWidgets/CheckboxWidget";

const Container = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 3px;
  background: var(--med-gray);
`;

const ListItem = styled.div`
  position: relative;
  height: 40px;
  background: var(--light-gray);
  border-bottom: 1px solid var(--med-gray);
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
`;

const ItemLabel = styled.div`
  font-size: 12px;
`;

export default function CheckboxList({ options, height, width, checkedItems, setCheckedItems, disabled }) {
  return (
    <Container style={{ height, width, minHeight: height, maxHeight: height, overflowY: "scroll" }}>
      {options.map((item, idx) => {
        return (
          <ListItem key={item} style={{ color: disabled[idx] ? "var(--dark-gray)" : "black" }}>
            <CheckboxWidget
              size={"12"}
              disabled={disabled[idx]}
              checkedState={checkedItems.includes(item)}
              handleCheckbox={(state) => setCheckedItems(item, state)}
            />
            <ItemLabel>{item}</ItemLabel>
          </ListItem>
        );
      })}
    </Container>
  );
}
