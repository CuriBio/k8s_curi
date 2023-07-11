import styled from "styled-components";

const formStyle = [
  `
  position: relative;
  width: 80%;
  height: 35px;
  min-height: 35px;
  padding: 5px;
  line-height: 2;
`,
];

const Field = styled.input(formStyle);
const Label = styled.label(formStyle);

export default function FormInput({
  name,
  label,
  placeholder,
  type = "text",
  value = "",
  onChangeFn,
  children,
  disabled = false,
  borderStyle = "none",
}) {
  return (
    <>
      {label ? <Label htmlFor={name}>{label}</Label> : null}
      <Field
        id={name}
        placeholder={disabled ? "Disabled" : placeholder}
        type={type}
        value={value}
        onChange={onChangeFn}
        style={{
          border: borderStyle,
          boxShadow: "rgba(0, 0, 0, 0.1) 1px 1px 1px 0px, rgba(0, 0, 0, 0.12) 1px 1px 3px 2px",
        }}
        disabled={disabled}
      />
      {children}
    </>
  );
}
