import styled from "styled-components";
import CheckboxWidget from "../basicWidgets/CheckboxWidget";
import { isArrayOfNumbers } from "../../utils/generic";
import FormInput from "../basicWidgets/FormInput";

const Container = styled.div`
  padding-top:1rem;
  left: 5%;
  top: 12%;
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
  margin:5rem 0 ;
`;

const TwoParamContainer = styled.div`
display: flex;
flex-direction: column;
height:100%;
`
const ParamContainer = styled.div`
  display: flex;
  flex-direction: row;
  overflow: visible;
  height: 70px;
  padding-top: 15px;
  height:10rem;
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
  border-radius: 5px;
  width: 60%;
  margin:.5rem 0 2rem 0;
`;
const AdvancedAnalysisContainer = styled.div`
border: 2px solid var(--dark-gray);
border-radius: 5px;
width: 60%;
margin-top:.5rem;
height:100%;
`;

const WAOverlay = styled.div`
  border-radius: 5px;
  z-index: 2;
  width:100%;
  height:100%;
  background-color: var(--dark-gray);
  opacity: 0.6;
  position:absolute;
`;
const Label = styled.label`
  width: 102%;
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

const WAOverlayContainer = styled.div`
position:relative;
z-index:2;
width:100%;
height:100%;
display:flex;
flex-flow:column;
align-items:center;
justify-content:end;
`

const InputErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 100%;
  overflow: visible;
`;

const FormModify = styled.div`
  display:flex;
  width:400px;
`

const WALabel = styled.span`
  background-color: var(--light-gray);
  bottom: 43%;
  border-radius: 6px;
  display: flex;
  align-items: center;
  width: 195px;
  font-size: 14px;
  z-index: 1;
  border: 2px solid var(--dark-gray);
  cursor: default;
  z-index:3;
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
  checkedWindow,
  setCheckedWindow,
  setAnalysisParams,
  checkedAdvanced,
  setCheckedAdvanced,
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
    if (newParams.prominenceFactorMin !== undefined) {
      validateProminenceFactorMin(updatedParams);
    }
    if (newParams.prominenceFactorMax !== undefined) {
      validateProminenceFactorMax(updatedParams);
    }
    if (newParams.widthFactorMin !== undefined) {
      validateWidthFactorMin(updatedParams)
    }
    if (newParams.widthFactorMax !== undefined) {
      validateWidthFactorMax(updatedParams)
    }
    if (newParams.prominenceFactorMin !== "" && newParams.prominenceFactorMax !== "") {
      validateProminenceEquality(updatedParams)
    }
    if (newParams.widthFactorMin !== "" && newParams.widthFactorMax !== "") {
      validateWidthEquality(updatedParams)
    }
    setAnalysisParams(updatedParams);
  };

  const validateProminenceEquality = (updatedParams) => {
    const min = updatedParams.prominenceFactorMin
    const max = updatedParams.prominenceFactorMax
    if (isValidPositiveNumber(min) && isValidPositiveNumber(max)) {
      if (!(parseFloat(min) < parseFloat(max))) {
        console.log("err")
        setParamErrors({
          ...paramErrors,
          prominenceFactorMin: "* min must be smaller than max",
        });
      } else {
        setParamErrors({
          ...paramErrors,
          prominenceFactorMin: "",
        });
      }
      console.log(paramErrors)
    }
  }
  const validateWidthEquality = (updatedParams) => {
    const min = updatedParams.widthFactorMin
    const max = updatedParams.widthFactorMax
    if (isValidPositiveNumber(min) && isValidPositiveNumber(max)) {
      if (!(parseFloat(min) < parseFloat(max))) {
        console.log("err")
        setParamErrors({
          ...paramErrors,
          widthFactorMin: "* min must be smaller than max",
        });
      } else {
        setParamErrors({
          ...paramErrors,
          widthFactorMin: "",
        });
      }
      console.log(paramErrors)
    }
  }

  const isValidPositiveNumber = (value) => {
    //check it is a number
    if (isNaN(parseFloat(value))) {
      return false
    }
    //check if it is a positive number
    if (parseFloat(value) < 0) {
      return false
    }
    return true
  }

  const validateProminenceFactorMin = (updatedParams) => {
    const newValue = updatedParams.prominenceFactorMin
    if (newValue === null || newValue === "") {
      setParamErrors({
        ...paramErrors,
        prominenceFactorMin: "",
      });
    } else if (isValidPositiveNumber(newValue)) {
      setParamErrors({
        ...paramErrors,
        prominenceFactorMin: "",
      });
    } else {
      setParamErrors({
        ...paramErrors,
        prominenceFactorMin: "* Must be a positive number",
      });
    }
  }
  const validateProminenceFactorMax = (updatedParams) => {
    const newValue = updatedParams.prominenceFactorMax
    if (newValue === null || newValue === "") {
      setParamErrors({
        ...paramErrors,
        prominenceFactorMax: "",
      });
    } else if (isValidPositiveNumber(newValue)) {
      setParamErrors({
        ...paramErrors,
        prominenceFactorMax: "",
      });
    } else {
      setParamErrors({
        ...paramErrors,
        prominenceFactorMax: "* Must be a positive number",
      });
    }
  }

  const validateWidthFactorMin = (updatedParams) => {
    const newValue = updatedParams.widthFactorMin
    console.log(newValue)
    if (newValue === null || newValue === "") {
      setParamErrors({
        ...paramErrors,
        widthFactorMin: "",
      });
    } else if (isValidPositiveNumber(newValue)) {
      setParamErrors({
        ...paramErrors,
        widthFactorMin: "",
      });
    } else {
      setParamErrors({
        ...paramErrors,
        widthFactorMin: "* Must be a positive number",
      });
    }
  }
  const validateWidthFactorMax = (updatedParams) => {
    const newValue = updatedParams.widthFactorMax
    if (newValue === null || newValue === "") {
      setParamErrors({
        ...paramErrors,
        widthFactorMax: "",
      });
    } else if (isValidPositiveNumber(newValue)) {
      setParamErrors({
        ...paramErrors,
        widthFactorMax: "",
      });
    } else {
      setParamErrors({
        ...paramErrors,
        widthFactorMax: "* Must be a positive number",
      });
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
        <WALabel>
          <CheckboxWidget
            color={"secondary"}
            size={"small"}
            handleCheckbox={(checkedWindow) => setCheckedWindow(checkedWindow)}
            checkedState={checkedWindow}
          />
          Use Window Analysis
        </WALabel>
        <WindowAnalysisContainer>
          <WAOverlayContainer>
            {checkedWindow || <WAOverlay />}
            <ParamContainer>
              <Label htmlFor="startTime">Start Time (s):</Label>
              <InputErrorContainer>
                <FormInput
                  name="startTime"
                  placeholder={checkedWindow ? "0" : ""}
                  value={!checkedWindow ? "" : inputVals.startTime}
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
                  placeholder={checkedWindow ? "(End of recording)" : ""}
                  value={!checkedWindow ? "" : inputVals.endTime}
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
          </WAOverlayContainer>
        </WindowAnalysisContainer>
        <WALabel>
          <CheckboxWidget
            color={"secondary"}
            size={"small"}
            handleCheckbox={(checkedAdvanced) => setCheckedAdvanced(checkedAdvanced)}
            checkedState={checkedAdvanced}
          />
          Use Advanced Analysis
        </WALabel>
        <AdvancedAnalysisContainer>
          <WAOverlayContainer>
            {checkedAdvanced || <WAOverlay />}
            <TwoParamContainer>
              <Label htmlFor="prominenceFactorMin">Prominence (uN):</Label>
              <InputErrorContainer>
                <label htmlFor="prominenceFactorMin">min</label>
                <FormModify>
                  <FormInput
                    name="prominenceFactorMin"
                    placeholder={checkedAdvanced ? "0" : ""}
                    value={!checkedAdvanced ? "" : inputVals.prominenceFactorMin}
                    onChangeFn={(e) => {
                      updateParams({
                        prominenceFactorMin: e.target.value,
                      });
                    }}
                  >
                    <ErrorText id="prominenceFactorMinError" role="errorMsg">
                      {errorMessages.prominenceFactorMin}
                    </ErrorText>
                  </FormInput>
                </FormModify>
                <label htmlFor="prominenceFactorMax">max</label>
                <FormModify>
                  <FormInput
                    name="prominenceFactorMax"
                    placeholder={checkedAdvanced ? "100" : ""}
                    value={!checkedAdvanced ? "" : inputVals.prominenceFactorMax}
                    onChangeFn={(e) => {
                      updateParams({
                        prominenceFactorMax: e.target.value,
                      });
                    }}
                  >
                    <ErrorText id="prominenceFactorMaxError" role="errorMsg">
                      {errorMessages.prominenceFactorMax}
                    </ErrorText>
                  </FormInput>
                </FormModify>

              </InputErrorContainer>
            </TwoParamContainer>
            <TwoParamContainer>
              <Label htmlFor="widthFactorMin">Width (ms):</Label>
              <InputErrorContainer>
                <label htmlFor="widthFactorMin">min</label>
                <FormModify>
                  <FormInput
                    name="widthFactorMin"
                    placeholder={checkedAdvanced ? "0" : ""}
                    value={!checkedAdvanced ? "" : inputVals.widthFactorMin}
                    onChangeFn={(e) => {
                      updateParams({
                        widthFactorMin: e.target.value,
                      });
                    }}
                  >
                    <ErrorText id="widthFactorMinError" role="errorMsg">
                      {errorMessages.widthFactorMin}
                    </ErrorText>

                  </FormInput>
                </FormModify>
                <label htmlFor="widthFactorMax">max</label>
                <FormModify>
                  <FormInput
                    name="widthFactorMax"
                    placeholder={checkedAdvanced ? "100" : ""}
                    value={!checkedAdvanced ? "" : inputVals.widthFactorMax}
                    onChangeFn={(e) => {
                      updateParams({
                        widthFactorMax: e.target.value,
                      });
                    }}
                  >
                    <ErrorText id="widthFactorMaxError" role="errorMsg">
                      {errorMessages.widthFactorMax}
                    </ErrorText>
                  </FormInput>
                </FormModify>
              </InputErrorContainer>
            </TwoParamContainer>
          </WAOverlayContainer>
        </AdvancedAnalysisContainer>
      </InputContainer>
    </Container>
  );
}
