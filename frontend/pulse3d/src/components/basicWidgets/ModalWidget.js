import Box from "@mui/material/Box";
import Modal from "@mui/material/Modal";
import ButtonWidget from "./ButtonWidget";
import styled from "styled-components";
import { useEffect, useState } from "react";

const ButtonContainer = styled.div`
  display: flex;
  flex-direction: row;
`;

const Header = styled.h2`
  width: 100%;
  text-align: center;
  font-weight: bold;
`;
const Text = styled.p`
  word-break: break-word;
  font-size: 18px;
  text-align: center;
  width: 100%;
  padding: 0 5%;
  position: relative;
`;
const ModalBody = styled.div`
  max-height: 60vh;
  overflow-y: scroll;
  overflow-x: hidden;
`;

export default function ModalWidget({
  open,
  closeModal,
  width = 700,
  buttons = ["Close"],
  header,
  labels,
  children,
}) {
  const style = {
    position: "absolute",
    top: "50%",
    left: "50%",
    transform: "translate(-50%, -50%)",
    width,
    bgcolor: "background.paper",
    boxShadow: 24,
    borderRadius: "10px",
    overflowY: "hidden",
  };

  const [disabled, setDisabled] = useState(false);

  useEffect(() => {
    // whem modal labels change, make sure to reset disabled buttons
    // important when a series of modals is used and just labels change
    setDisabled(false);
  }, [labels]);

  return (
    <div>
      <Modal open={open}>
        <Box sx={style}>
          <Header>{header}</Header>
          <ModalBody>
            {labels.map((text, idx) => {
              return <Text key={idx}>{text}</Text>;
            })}
            {children}
          </ModalBody>
          <ButtonContainer>
            {buttons.map((label, idx) => {
              return (
                <ButtonWidget
                  disabled={disabled}
                  backgroundColor={disabled ? "var(--dark-gray)" : "var(--dark-blue)"}
                  key={idx}
                  label={label}
                  clickFn={() => {
                    setDisabled(true);
                    closeModal(idx, label);
                  }}
                />
              );
            })}
          </ButtonContainer>
        </Box>
      </Modal>
    </div>
  );
}
