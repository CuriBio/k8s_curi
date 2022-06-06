import styled from "styled-components";

const Button = styled.button(
  ({ props }) => `
  background-color: ${props.isSelected ? "var(--teal-green)" : props.backgroundColor || "var(--dark-blue)"};
  color: var(--light-gray);
  font-size: inherit;
  border: none;
  top: ${props.top || "0px"};
  left: ${props.left || "0px"};
  height: ${props.height || "15%"};
  width: ${props.width || "inherit"};
  position: ${props.position || "inherit"};
  border-radius: ${props.borderRadius || "0px"};

  &:hover {
    background-color: ${props.disabled || "var(--teal-green)"};
    cursor:${props.disabled || "pointer"};
  }
  `,
);

const ButtonWidget = (props) => {
  return (
    <Button
      onClick={() => {
        if (!props.isSelected && !props.disabled) props.clickFn(props.label); // only if not already selected emit event
      }}
      props={props}
    >
      {props.label}
    </Button>
  );
};

export default ButtonWidget;
