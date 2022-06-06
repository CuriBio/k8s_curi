import styled from "styled-components";

const Button = styled.button(
  ({ props }) => `
    background-color: ${
      props.isSelected
        ? "var(--teal-green)"
        : props.backgroundColor || "var(--dark-blue)"
    };
    color: var(--light-gray);
    font-size: inherit;
    border: none;
    height: ${props.height || "15%"};
    width: ${props.width || "inherit"};

    &:hover {
        background-color: ${props.disabled || "var(--teal-green)"};
        cursor:${props.disabled || "pointer"};
    }
  `
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
