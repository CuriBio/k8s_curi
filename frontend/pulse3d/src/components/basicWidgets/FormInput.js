import styled from "styled-components";

const formStyle = [
  `
  position: relative;
  width: 80%;
  height: 40px;
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
          boxShadow:
            "0px 2px 2px -3px rgb(0 0 0 / 20%), 0px 5px 5px 0px rgb(0 0 0 / 10%), 0px 2px 5px 2px rgb(0 0 0 / 12%)",
        }}
        disabled={disabled}
      />
      {children}
    </>
  );
}
