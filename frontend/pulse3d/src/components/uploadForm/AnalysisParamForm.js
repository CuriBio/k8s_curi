import styled from "styled-components";
import CheckboxWidget from "../basicWidgets/CheckboxWidget";
import { isArrayOfNumbers } from "../../utils/generic";

const Container = styled.div`
  left: 5%;
  top: 12%;
  height: 55%;
  width: 90%;
  position: relative;
  display: flex;
  flex-direction: row;
  border: solid;
  justify-content: center;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 7px;
  background-color: var(--light-gray);
`;

const ParamContainer = styled.div`
  display: flex;
  flex-direction: row;
  overflow: visible;
  height: 70px;
  padding-top: 15px;
`;

const InputContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  align-items: center;
  width: 90%;
`;

const WindowAnalysisContainer = styled.div`
  border: 2px solid var(--dark-gray);
  height: 47%;
  border-radius: 5px;
  width: 60%;
  display: flex;
  flex-direction: column;
  justify-content: center;
`;

const WAOverlay = styled.div`
  border-radius: 5px;
  background-color: black;
  z-index: 2;
  border-radius: 5px;
  width: 54%;
  position: absolute;
  height: 47%;
  top: 41%;
  background-color: var(--dark-gray);
  opacity: 0.6;
`;

const Field = styled.input`
  width: 80%;
  position: relative;
  height: 35px;
  padding: 5px;
  border-radius: 5px;
  display: flex;
  justify-content: center;
  border-color: var(--dark-gray);
  line-height: 3;
`;

const Label = styled.label`
  width: 70%;
  position: relative;
  height: 40px;
  padding: 5px;
  border-radius: 5px;
  display: flex;
  justify-content: end;
  padding-right: 5%;
  white-space: nowrap;
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  font-size: 13px;
`;

const InputErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 100%;
  overflow: visible;
`;

const WALabel = styled.span`
  background-color: var(--light-gray);
  bottom: 54%;
  border-radius: 6px;
  position: absolute;
  left: 25%;
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 195px;
  font-size: 14px;
  z-index: 3;
  border: 2px solid var(--dark-gray);
  cursor: default;
`;

export default function AnalysisParamForm({
  inputVals,
  errorMessages,
  checked,
  setChecked,
  setAnalysisParams,
  paramErrors,
  setParamErrors,
  analysisParams,
}) {
  const updateParams = (newParams) => {
    const updatedParams = { ...analysisParams, ...newParams };

    if (newParams.twitchWidths !== undefined) {
      validateTwitchWidths(updatedParams);
    }
    if (newParams.startTime !== undefined || newParams.endTime !== undefined) {
      // need to validate start and end time together
      validateWindowBounds(updatedParams);
    }

    setAnalysisParams(updatedParams);
  };

  const validateTwitchWidths = (updatedParams) => {
    const newValue = updatedParams.twitchWidths;
    let formattedTwitchWidths;
    if (newValue === null || newValue === "") {
      formattedTwitchWidths = "";
    } else {
      let twitchWidthArr;
      // make sure it's a valid list
      try {
        twitchWidthArr = JSON.parse(`[${newValue}]`);
      } catch (e) {
        setParamErrors({
          ...paramErrors,
          twitchWidths: "*Must be comma-separated, positive numbers",
        });
        return;
      }
      // make sure it's an array of positive numbers
      if (isArrayOfNumbers(twitchWidthArr, true)) {
        formattedTwitchWidths = Array.from(new Set(twitchWidthArr));
        console.log("formattedTwitchWidths:", formattedTwitchWidths);
      } else {
        console.log(`Invalid twitchWidths: ${newValue}`);
        setParamErrors({
          ...paramErrors,
          twitchWidths: "*Must be comma-separated, positive numbers",
        });
        return;
      }
    }
    setParamErrors({ ...paramErrors, twitchWidths: "" });
    updatedParams.twitchWidths = formattedTwitchWidths;
  };

  const validateWindowBounds = (updatedParams) => {
    const { startTime, endTime } = updatedParams;
    const updatedParamErrors = { ...paramErrors };

    for (const [boundName, boundValueStr] of Object.entries({
      startTime,
      endTime,
    })) {
      let error = "";
      if (boundValueStr) {
        // checks if positive number, no other characters allowed
        const numRegEx = new RegExp("^([0-9]+(?:[.][0-9]*)?|.[0-9]+)$");
        if (!numRegEx.test(boundValueStr)) {
          error = "*Must be a non-negative number";
        } else {
          const boundValue = +boundValueStr;
          updatedParams[boundName] = boundValue;
        }
      }

      updatedParamErrors[boundName] = error;
    }

    if (
      !updatedParamErrors.startTime &&
      !updatedParamErrors.endTime &&
      updatedParams.startTime &&
      updatedParams.endTime &&
      updatedParams.startTime >= updatedParams.endTime
    ) {
      updatedParamErrors.endTime = "*Must be greater than Start Time";
    }
    setParamErrors(updatedParamErrors);
  };

  return (
    <Container>
      <InputContainer>
        <ParamContainer style={{ width: "60%" }}>
          <Label htmlFor="twitchWidths">Twitch Widths (%):</Label>
          <InputErrorContainer>
            <Field
              id="twitchWidths"
              placeholder="50, 90"
              value={inputVals.twitchWidths}
              onChange={(e) => {
                updateParams({
                  twitchWidths: e.target.value,
                });
              }}
            />
            <ErrorText id="twitchWidthError" role="errorMsg">
              {errorMessages.twitchWidths}
            </ErrorText>
          </InputErrorContainer>
        </ParamContainer>
        {checked || <WAOverlay />}
        <WindowAnalysisContainer>
          <WALabel>
            <CheckboxWidget
              color={"secondary"}
              size={"small"}
              handleCheckbox={(checked) => setChecked(checked)}
              checkedState={checked}
            />
            Use Window Analysis
          </WALabel>

          <ParamContainer>
            <Label htmlFor="startTime">Start Time (s):</Label>
            <InputErrorContainer>
              <Field
                id="startTime"
                placeholder={checked ? "0" : ""}
                value={!checked ? "" : inputVals.startTime}
                onChange={(e) => {
                  updateParams({
                    startTime: e.target.value,
                  });
                }}
              />
              <ErrorText id="startTimeError" role="errorMsg">
                {errorMessages.startTime}
              </ErrorText>
            </InputErrorContainer>
          </ParamContainer>
          <ParamContainer>
            <Label htmlFor="endTime">End Time (s):</Label>
            <InputErrorContainer>
              <Field
                id="endTime"
                placeholder={checked ? "(End of recording)" : ""}
                value={!checked ? "" : inputVals.endTime}
                onChange={(e) => {
                  updateParams({
                    endTime: e.target.value,
                  });
                }}
              />
              <ErrorText id="endTimeError" role="errorMsg">
                {errorMessages.endTime}
              </ErrorText>
            </InputErrorContainer>
          </ParamContainer>
        </WindowAnalysisContainer>
      </InputContainer>
    </Container>
  );
}
