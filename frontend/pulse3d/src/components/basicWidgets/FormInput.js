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
}) {
  return (
    <>
      {label ? <Label htmlFor={name}>{label}</Label> : null}
      <Field
        id={name}
        placeholder={placeholder}
        type={type}
        value={value}
        onChange={onChangeFn}
      />
      {children}
    </>
  );
}
