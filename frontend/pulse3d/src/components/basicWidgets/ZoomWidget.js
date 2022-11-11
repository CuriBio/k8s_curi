import * as React from "react";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import styled from "styled-components";
import { styled as muiStyled } from "@mui/material/styles";

const Container = styled.div`
  display: flex;
  flex-direction: row;
  justify-content: space-evenly;
  padding: 5px;
`;

const MinusIcon = muiStyled(RemoveCircleOutlineIcon)`
  :hover {
    fill: var(--teal-green);
    cursor: pointer;
  }
`;

const PlusIcon = muiStyled(AddCircleOutlineIcon)`
  :hover {
    fill: var(--teal-green);
    cursor: pointer;
  }
`;

export default function ZoomWidget({ size = "16px", zoomIn, zoomOut }) {
  return (
    <Container>
      <MinusIcon sx={{ fontSize: size }} onClick={zoomOut} />
      <PlusIcon sx={{ fontSize: size }} onClick={zoomIn} />
    </Container>
  );
}
