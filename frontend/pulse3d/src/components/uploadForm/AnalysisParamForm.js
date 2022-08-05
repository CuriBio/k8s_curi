import styled from "styled-components";
import CheckboxWidget from "../basicWidgets/CheckboxWidget";
import { isArrayOfNumbers } from "../../utils/generic";
import FormInput from "../basicWidgets/FormInput";

const Container = styled.div`
  padding-top:1rem;
  left: 5%;
  top: 12%;
  height: 50%;
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
  margin-top:50px;
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
  width: 53.6%;
  position: absolute;
  height: 45%;
  background-color: var(--dark-gray);
  opacity: 0.6;
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
  bottom: 48%;
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

const AdditionalParamLabel = styled.span`
  background-color: var(--light-gray);
  border-radius: 6px;
  position: absolute;
  left: 25%;
  display: flex;
  align-items: center;
  width: 380px;
  font-size: 17px;
  z-index: 3;
  border: 2px solid var(--dark-gray);
  cursor: default;
  height: 50px;
  justify-content: center;
  top: -21px;
  left: 5%;
  font-weight: 900;
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
    if (newParams.prominenceFactor !== undefined) {
      validatePromineceFactor(updateParams);
    }
    if (newParams.widthFactor !== undefined) {
      validateWidthFactor(updateParams)
    }
    setAnalysisParams(updatedParams);
  };

  const validateWidthFactor = (updateParams) => {
    const newValue = updateParams.widthFactor;
    try {
      parseFloat(newValue)
    } catch (e) {
      setParamErrors({
        ...paramErrors,
        widthFactor: "*Must be a positive number",
      });
      return;
    }
    if (parseFloat(newValue) < 0) {
      setParamErrors({
        ...paramErrors,
        widthFactor: "*Must be a positive number",
      });
      return;
    }
  }

  const validatePromineceFactor = (updateParams) => {
    const newValue = updateParams.prominenceFactor;
    try {
      parseFloat(newValue)
    } catch (e) {
      setParamErrors({
        ...paramErrors,
        prominenceFactor: "*Must be a positive number",
      });
      return;
    }
    if (parseFloat(newValue) < 0) {
      setParamErrors({
        ...paramErrors,
        prominenceFactor: "*Must be a positive number",
      });
      return;
    }
  }

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
      <AdditionalParamLabel>
        Additional Analysis Params (Optional)
      </AdditionalParamLabel>
      <InputContainer>

        <ParamContainer style={{ width: "60%" }}>
          <Label htmlFor="prominenceFactor">Prominence Factor (units):</Label>
          <InputErrorContainer>
            <FormInput
              name="prominenceFactor"
              placeholder={"10"}
              value={inputVals.prominenceFactor}
              onChangeFn={(e) => {
                updateParams({
                  prominenceFactor: e.target.value,
                });
              }}
            >
              <ErrorText id="prominenceFactorError" role="errorMsg">
                {errorMessages.prominenceFactor}
              </ErrorText>
            </FormInput>
          </InputErrorContainer>
        </ParamContainer>

        <ParamContainer style={{ width: "60%" }}>
          <Label htmlFor="widthFactor">Width Factor:</Label>
          <InputErrorContainer>
            <FormInput
              name="widthFactor"
              placeholder={"5"}
              value={inputVals.widthFactor}
              onChangeFn={(e) => {
                updateParams({
                  widthFactor: e.target.value,
                });
              }}
            >
              <ErrorText id="widthFactorError" role="errorMsg">
                {errorMessages.widthFactor}
              </ErrorText>
            </FormInput>
          </InputErrorContainer>
        </ParamContainer>

        <ParamContainer style={{ width: "60%" }}>
          <Label htmlFor="twitchWidths">Twitch Width:</Label>
          <InputErrorContainer>
            <FormInput
              name="twitchWidths"
              placeholder={"50, 90"}
              value={inputVals.twitchWidths}
              onChangeFn={(e) => {
                updateParams({
                  twitchWidths: e.target.value,
                });
              }}
            >
              <ErrorText id="twitchWidthError" role="errorMsg">
                {errorMessages.twitchWidths}
              </ErrorText>
            </FormInput>
          </InputErrorContainer>
        </ParamContainer>
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
          {checked || <WAOverlay />}
          <ParamContainer>
            <Label htmlFor="startTime">Start Time (s):</Label>
            <InputErrorContainer>
              <FormInput
                name="startTime"
                placeholder={checked ? "0" : ""}
                value={!checked ? "" : inputVals.startTime}
                onChangeFn={(e) => {
                  updateParams({
                    startTime: e.target.value,
                  });
                }}
              >
                <ErrorText id="startTimeError" role="errorMsg">
                  {errorMessages.startTime}
                </ErrorText>
              </FormInput>
            </InputErrorContainer>
          </ParamContainer>
          <ParamContainer>
            <Label htmlFor="endTime">End Time (s):</Label>
            <InputErrorContainer>
              <FormInput
                name="endTime"
                placeholder={checked ? "(End of recording)" : ""}
                value={!checked ? "" : inputVals.endTime}
                onChangeFn={(e) => {
                  updateParams({
                    endTime: e.target.value,
                  });
                }}
              >
                <ErrorText id="endTimeError" role="errorMsg">
                  {errorMessages.endTime}
                </ErrorText>
              </FormInput>
            </InputErrorContainer>
          </ParamContainer>
        </WindowAnalysisContainer>
      </InputContainer>
    </Container>
  );
}
