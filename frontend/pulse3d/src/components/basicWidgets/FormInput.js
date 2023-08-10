import styled from "styled-components";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";

const TooltipText = styled.span`
  font-size: 15px;
`;

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
  tooltipText,
  tooltipIconStyle = { fontSize: 20, margin: "0px 10px" },
  disabled = false,
  borderStyle = "none",
}) {
  return (
    <>
      {label && (
        <Label htmlFor={name}>
          {label}
          {tooltipText && (
            <Tooltip title={<TooltipText>{tooltipText}</TooltipText>}>
              <InfoOutlinedIcon sx={tooltipIconStyle} />
            </Tooltip>
          )}
        </Label>
      )}
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
