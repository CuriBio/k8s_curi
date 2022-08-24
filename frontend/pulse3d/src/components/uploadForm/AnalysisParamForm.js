import styled from "styled-components";
import CheckboxWidget from "../basicWidgets/CheckboxWidget";
import { isArrayOfNumbers } from "../../utils/generic";
import FormInput from "../basicWidgets/FormInput";

const Container = styled.div`
  padding-top: 1rem;
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
  margin-top: 8%;
  margin-bottom: 4;
`;

const TwoParamContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  align-items: center;
  padding: 1rem;
`;
const ParamContainer = styled.div`
  display: flex;
  flex-direction: row;
  overflow: visible;
  height: 70px;
  padding: 15px 0 10px 0;
  height: 70px;
  width: 320px;
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
  margin-top: 4rem;
`;
const AdvancedAnalysisContainer = styled.div`
  border: 2px solid var(--dark-gray);
  border-radius: 5px;
  width: 60%;
  height: 100%;
  margin-top: 4rem;
  margin-bottom: 4rem;
`;

const WAOverlay = styled.div`
  border-radius: 5px;
  z-index: 2;
  width: 100%;
  height: 100%;
  background-color: var(--dark-gray);
  opacity: 0.6;
  position: absolute;
`;
const Label = styled.label`
  width: 102%;
  position: relative;
  height: 25px;
  padding: 10px;
  border-radius: 5px;
  display: flex;
  justify-content: center;
  padding-right: 5%;
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

const WAOverlayContainer = styled.div`
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  display: flex;
  flex-flow: column;
  align-items: center;
  justify-content: end;
`;

const InputErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 100%;
  overflow: visible;
`;

const FormModify = styled.div`
  display: flex;
  width: 400px;
`;

const WALabel = styled.span`
  background-color: var(--light-gray);
  border-radius: 6px;
  display: flex;
  align-items: center;
  font-size: 14px;
  border: 2px solid var(--dark-gray);
  cursor: default;
  z-index: 3;
  position: absolute;
  right: 55%;
  bottom: 94%;
  width: 205px;
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
    setAllErrorMessagesBlank();
    const updatedParams = { ...analysisParams, ...newParams };

    if (newParams.twitchWidths) {
      validateTwitchWidths(updatedParams);
    }
    if (newParams.startTime || newParams.endTime) {
      // need to validate start and end time together
      validateWindowBounds(updatedParams);
    }
    if (newParams.prominenceFactorPeaks) {
      validateAdvancedParams(updatedParams, "prominenceFactorPeaks");
    }
    if (newParams.prominenceFactorValleys) {
      validateAdvancedParams(updatedParams, "prominenceFactorValleys");
    }
    if (newParams.widthFactorPeaks) {
      validateAdvancedParams(updatedParams, "widthFactorPeaks");
    }
    if (newParams.widthFactorValleys) {
      validateAdvancedParams(updatedParams, "widthFactorValleys");
    }
    if (newParams.maxY) {
      validateMaxY(updatedParams);
    }
    setAnalysisParams(updatedParams);
  };

  const setAllErrorMessagesBlank = () => {
    for (const param in paramErrors) {
      setParamErrors({
        ...paramErrors,
        [param]: "",
      });
    }
  };

  const validateMaxY = (updatedParams) => {
    let newValue = updatedParams["maxY"];
    //check both are numbers
    if (isNaN(newValue)) {
      setParamErrors({
        ...paramErrors,
        maxY: "* Must be a single number",
      });
      return;
    }
    if (newValue <= 0) {
      setParamErrors({
        ...paramErrors,
        maxY: "* Must be greater than 0",
      });
      return;
    }
    setParamErrors({
      ...paramErrors,
      maxY: "",
    });
  };

  const isValidPositiveNumber = (value) => {
    return +value > 0;
  };

  const validateAdvancedParams = (updatedParams, paramName) => {
    const newValue = updatedParams[paramName];
    if (newValue === null || newValue === "") {
      setParamErrors({
        ...paramErrors,
        [paramName]: "",
      });
    } else if (isValidPositiveNumber(newValue)) {
      setParamErrors({
        ...paramErrors,
        [paramName]: "",
      });
    } else {
      setParamErrors({
        ...paramErrors,
        [paramName]: "* Must be a positive number",
      });
    }
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
      <AdditionalParamLabel>
        Additional Analysis Params (Optional)
      </AdditionalParamLabel>
      <InputContainer>
        <ParamContainer style={{ width: "33%", marginTop: "2%" }}>
          <Label
            htmlFor="maxY"
            title="Specifies the maximum y-axis range of Active Twitch Force in the output xlsx."
          >
            Y-Axis Range (µN):
          </Label>
          <InputErrorContainer>
            <FormInput
              name="maxY"
              placeholder={"Auto find max y"}
              value={inputVals.maxY}
              onChangeFn={(e) => {
                updateParams({
                  maxY: e.target.value,
                });
              }}
            >
              <ErrorText id="maxYError" role="errorMsg">
                {errorMessages.maxY}
              </ErrorText>
            </FormInput>
          </InputErrorContainer>
        </ParamContainer>

        <ParamContainer style={{ width: "33%", marginTop: "2%" }}>
          <Label
            htmlFor="twitchWidths"
            title="Specifies which twitch width values to add to the per twitch metrics sheet and aggregate metrics sheet."
          >
            Twitch Width:
          </Label>
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
          <WAOverlayContainer>
            <WALabel>
              <CheckboxWidget
                color={"secondary"}
                size={"small"}
                handleCheckbox={(checkedWindow) =>
                  setCheckedWindow(checkedWindow)
                }
                checkedState={checkedWindow}
              />
              Use Window Analysis
            </WALabel>
            {checkedWindow || <WAOverlay />}
            <ParamContainer>
              <Label
                htmlFor="startTime"
                title="Specifies the earliest timepoint (in seconds) to use in analysis."
              >
                Start Time (s):
              </Label>
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
              <Label
                htmlFor="endTime"
                title="Specifies the latest timepoint (in seconds) to use in analysis."
              >
                End Time (s):
              </Label>
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
        <AdvancedAnalysisContainer>
          <WAOverlayContainer>
            <WALabel>
              <CheckboxWidget
                color={"secondary"}
                size={"small"}
                handleCheckbox={(checkedAdvanced) =>
                  setCheckedAdvanced(checkedAdvanced)
                }
                checkedState={checkedAdvanced}
              />
              Use Advanced Analysis
            </WALabel>
            {checkedAdvanced || <WAOverlay />}
            <TwoParamContainer>
              <Label
                htmlFor="prominenceFactorPeaks"
                title="Specifies the minimum required vertical distance between a local max and its lowest contour line to be classified as a peak."
              >
                Prominence (µN):
              </Label>
              <InputErrorContainer>
                <label htmlFor="prominenceFactorPeaks">Peaks</label>
                <FormModify>
                  <FormInput
                    name="prominenceFactorPeaks"
                    placeholder={checkedAdvanced ? "6" : ""}
                    value={
                      !checkedAdvanced ? "" : inputVals.prominenceFactorPeaks
                    }
                    onChangeFn={(e) => {
                      updateParams({
                        prominenceFactorPeaks: e.target.value,
                      });
                    }}
                  >
                    <ErrorText id="prominenceFactorPeaksError" role="errorMsg">
                      {errorMessages.prominenceFactorPeaks}
                    </ErrorText>
                  </FormInput>
                </FormModify>
                <label htmlFor="prominenceFactorValleys">Valleys</label>
                <FormModify>
                  <FormInput
                    name="prominenceFactorValleys"
                    placeholder={checkedAdvanced ? "6" : ""}
                    value={
                      !checkedAdvanced ? "" : inputVals.prominenceFactorValleys
                    }
                    onChangeFn={(e) => {
                      updateParams({
                        prominenceFactorValleys: e.target.value,
                      });
                    }}
                  >
                    <ErrorText
                      id="prominenceFactorValleysError"
                      role="errorMsg"
                    >
                      {errorMessages.prominenceFactorValleys}
                    </ErrorText>
                  </FormInput>
                </FormModify>
              </InputErrorContainer>
            </TwoParamContainer>
            <TwoParamContainer>
              <Label
                htmlFor="widthFactorPeaks"
                title="Specifies the minimum required width of the base of a local max to be classified as a peak."
              >
                Width (ms):
              </Label>
              <InputErrorContainer>
                <label htmlFor="widthFactorPeaks">Peaks</label>
                <FormModify>
                  <FormInput
                    name="widthFactorPeaks"
                    placeholder={checkedAdvanced ? "7" : ""}
                    value={!checkedAdvanced ? "" : inputVals.widthFactorPeaks}
                    onChangeFn={(e) => {
                      updateParams({
                        widthFactorPeaks: e.target.value,
                      });
                    }}
                  >
                    <ErrorText id="widthFactorPeaksError" role="errorMsg">
                      {errorMessages.widthFactorPeaks}
                    </ErrorText>
                  </FormInput>
                </FormModify>
                <label htmlFor="widthFactorValleys">Valleys</label>
                <FormModify>
                  <FormInput
                    name="widthFactorValleys"
                    placeholder={checkedAdvanced ? "7" : ""}
                    value={!checkedAdvanced ? "" : inputVals.widthFactorValleys}
                    onChangeFn={(e) => {
                      updateParams({
                        widthFactorValleys: e.target.value,
                      });
                    }}
                  >
                    <ErrorText id="widthFactorValleysError" role="errorMsg">
                      {errorMessages.widthFactorValleys}
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
