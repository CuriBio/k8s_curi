import styled from "styled-components";
import CircularSpinner from "./CircularSpinner";
const Button = styled.button(
  ({ props }) => `
  background-color: ${props.backgroundColor || "var(--dark-blue)"};
  color: ${props.color || "var(--light-gray)"};
  font-size: inherit;
  border: none;
  width: 100%;
  height: 100%;
  position: ${props.position || "inherit"};
  border-radius: ${props.borderRadius || "0px"};
  font-size: ${props.fontSize || "18px"};
  box-shadow: 3px 3px 3px 0px rgb(0 0 0 / 30%), 7px 7px 7px 0px rgb(0 0 0 / 10%);
  &:hover {
    background-color: ${props.disabled || "var(--teal-green)"};
    cursor:${props.disabled || "pointer"};
  }
  `
);

const ProgressSpinner = styled.div(
  ({ props }) => `
  position: absolute;
  align-items: center;
  display: flex;
  justify-self: center;
  height: ${props.height || "60px"};
  align-items: center;
`
);

const Container = styled.div(
  ({ props }) => `
  display: flex;
  justify-content: center;
  position: relative;
  width: ${props.width || "100%"};
  height: ${props.height || "60px"};
  top: ${props.top || "0px"};
  left: ${props.left || "0px"};
`
);

// TODO should this automatically disable itself if props.inProgress === true ?
const ButtonWidget = (props) => {
  return (
    <Container props={props}>
      <Button
        onClick={() => {
          if (!props.isSelected && !props.disabled) props.clickFn(props.label); // only if not already selected and enabled, emit event
        }}
        props={props}
      >
        {props.label}
      </Button>{" "}
      {props.inProgress && (
        <ProgressSpinner props={props}>
          <CircularSpinner />
        </ProgressSpinner>
      )}
    </Container>
  );
};

export default ButtonWidget;
