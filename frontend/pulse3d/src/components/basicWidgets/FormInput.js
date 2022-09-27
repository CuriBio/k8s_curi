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
}) {
  return (
    <>
      {label ? <Label htmlFor={name}>{label}</Label> : null}
      {disabled ? (
        <Field
          id={name}
          placeholder={"Disabled"}
          type={type}
          value={value}
          onChange={onChangeFn}
          style={{
            border: "none",
            boxShadow:
              "0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%), 0px 3px 14px 2px rgb(0 0 0 / 12%)",
          }}
          readOnly
        />
      ) : (
        <Field
          id={name}
          placeholder={placeholder}
          type={type}
          value={value}
          onChange={onChangeFn}
          style={{
            border: "none",
            boxShadow:
              "0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%), 0px 3px 14px 2px rgb(0 0 0 / 12%)",
          }}
        />
      )}
      {children}
    </>
  );
}
