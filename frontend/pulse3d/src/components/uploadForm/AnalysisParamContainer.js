import styled from "styled-components";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";
import FormInput from "@/components/basicWidgets/FormInput";

const ParamContainer = styled.div`
  display: grid;
  grid-template-columns: 60% 50%;
  height: 70px;
  padding: 15px 0 10px 0;
  height: 70px;
  width: 450px;
`;

const Label = styled.label`
  position: relative;
  height: 25px;
  padding: 10px;
  border-radius: 5px;
  display: flex;
  justify-content: left;
  padding-right: 3%;
  white-space: nowrap;
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 150%;
  font-size: 13px;
`;

const WarningText = styled.span`
  color: darkorange;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 150%;
  font-size: 13px;
`;

const InputErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 60px;
  width: 70%;
`;

const TooltipText = styled.span`
  font-size: 15px;
`;

export default function AnalysisParamContainer({
  label,
  name,
  tooltipText,
  iconStyle = { fontSize: 20, margin: "0px 10px" },
  additionalErrorStyle,
  additionalLabelStyle,
  additionalParamStyle,
  placeholder,
  value,
  changeFn,
  errorMsg,
  warningMsg,
  children,
  disabled = false,
}) {
  return (
    <ParamContainer style={additionalParamStyle}>
      <Label htmlFor={name} style={additionalLabelStyle}>
        {label}:
        <Tooltip title={<TooltipText>{tooltipText}</TooltipText>}>
          <InfoOutlinedIcon sx={iconStyle} />
        </Tooltip>
      </Label>
      {children}
      {!children && (
        <InputErrorContainer style={additionalErrorStyle}>
          <FormInput
            name={name}
            placeholder={placeholder}
            value={value}
            onChangeFn={changeFn}
            disabled={disabled}
          >
            {errorMsg && (
              <ErrorText id={`${name}Error`} role="errorMsg">
                {errorMsg}
              </ErrorText>
            )}
            {(!errorMsg || errorMsg === "") && warningMsg && (
              <WarningText id={`${name}Warning`} role="warningMsg">
                {warningMsg}
              </WarningText>
            )}
          </FormInput>
        </InputErrorContainer>
      )}
    </ParamContainer>
  );
}
