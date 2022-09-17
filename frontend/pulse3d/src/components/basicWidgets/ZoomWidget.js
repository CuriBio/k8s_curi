import * as React from "react";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import styled from "styled-components";

const Container = styled.div`
  display: flex;
  flex-direction: row;
  justify-content: space-evenly;
  padding: 5px;
`;

export default function ZoomWidget({ size }) {
  return (
    <Container>
      <RemoveCircleOutlineIcon sx={{ fontSize: size }} />
      <AddCircleOutlineIcon sx={{ fontSize: size }} />
    </Container>
  );
}
