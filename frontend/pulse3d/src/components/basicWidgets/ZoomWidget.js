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

const MinusIcon = styled((props) => <RemoveCircleOutlineIcon {...props} />)(
  ({ size }) => ({
    fontSize: size,
    "&:hover": {
      fill: "var(--teal-green)",
      cursor: "pointer",
    },
  })
);

const PlusIcon = styled((props) => <AddCircleOutlineIcon {...props} />)(
  ({ size }) => ({
    fontSize: size,
    "&:hover": {
      fill: "var(--teal-green)",
      cursor: "pointer",
    },
  })
);

export default function ZoomWidget({ size = "16px", zoomIn, zoomOut }) {
  return (
    <Container>
      <MinusIcon size={size} onClick={zoomOut} />
      <PlusIcon size={size} onClick={zoomIn} />
    </Container>
  );
}
