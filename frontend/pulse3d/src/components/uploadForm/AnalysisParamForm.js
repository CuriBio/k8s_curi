import styled from "styled-components";
import CheckboxWidget from "../basicWidgets/CheckboxWidget";
import { isArrayOfNumbers } from "../../utils/generic";
import FormInput from "../basicWidgets/FormInput";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";

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

const TooltipText = styled.span`
  font-size: 15px;
`;

const DropDownContainer = styled.div`
  width: 25%;
  height: 125%;
  background: white;
  border-radius: 5px;
`;

export default function AnalysisParamForm({
  checkedBaseline,
  setCheckedBaseline,
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
  pulse3dVersions,
  resetDropDown,
}) {
  const updateParams = (newParams) => {
    const updatedParams = { ...analysisParams, ...newParams };

    if ("twitchWidths" in newParams) {
      validateTwitchWidths(updatedParams);
    }
    if ("startTime" in newParams || "endTime" in newParams) {
      // need to validate start and end time together
      validateWindowBounds(updatedParams);
    }
    for (const paramName of [
      "prominenceFactorPeaks",
      "prominenceFactorValleys",
      "widthFactorPeaks",
      "widthFactorValleys",
      "maxY",
      "baseToPeak",
      "peakToBase",
    ]) {
      if (paramName in newParams) {
        validatePositiveNumber(updatedParams, paramName, false);
      }
    }
    setAnalysisParams(updatedParams);
  };

  const checkPositiveNumberEntry = (value, allowZero = true) => {
    const minValue = allowZero ? 0 : Number.MIN_VALUE;
    return value === null || value === "" || value >= minValue;
  };

  const validatePositiveNumber = (
    updatedParams,
    paramName,
    allowZero = true
  ) => {
    const newValue = updatedParams[paramName];

    let errorMsg = "";
    if (!checkPositiveNumberEntry(newValue, allowZero)) {
      errorMsg = allowZero
        ? "*Must be a positive number"
        : "*Must be a positive, non-zero number";
    }
    setParamErrors({ ...paramErrors, [paramName]: errorMsg });
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

    for (const [boundName, boundValue] of Object.entries({
      startTime,
      endTime,
    })) {
      let error = "";

      // only perform this check if something has actually been entered
      if (boundValue) {
        const allowZero = boundName === "startTime";
        if (!checkPositiveNumberEntry(boundValue, allowZero)) {
          error = "*Must be a positive number";
        } else {
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

  const handleDropDownSelect = (idx) => {
    updateParams({
      pulse3dVersion: pulse3dVersions[idx],
    });
  };

  return (
    <Container>
      <AdditionalParamLabel>
        Additional Analysis Params (Optional)
      </AdditionalParamLabel>
      <InputContainer>
        <ParamContainer style={{ width: "43%", marginTop: "2%" }}>
          <Label
            htmlFor="pulse3dVersion"
            style={{ width: "57%", paddingLeft: "16%" }}
          >
            Pulse3d Version:
            <Tooltip
              title={
                <TooltipText>
                  {
                    "Specifies which version of the pulse3d analysis software to use."
                  }
                </TooltipText>
              }
            >
              <InfoOutlinedIcon />
            </Tooltip>
          </Label>
          <DropDownContainer>
            <DropDownWidget
              options={pulse3dVersions}
              label="Select"
              reset={
                resetDropDown /* TODO reset if user unchecks use advanced params once the entire section is under a single checkbox. Also remove this value entirely */
              }
              handleSelection={handleDropDownSelect}
            />
          </DropDownContainer>
        </ParamContainer>
        <ParamContainer style={{ width: "33%", marginTop: "2%" }}>
          <Label htmlFor="maxY">
            Y-Axis Range (µN):
            <Tooltip
              title={
                <TooltipText>
                  {
                    "Specifies the maximum y-axis bound of graphs generated in the output xlsx file."
                  }
                </TooltipText>
              }
            >
              <InfoOutlinedIcon />
            </Tooltip>
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
          <Label htmlFor="twitchWidths">
            Twitch Widths (%):
            <Tooltip
              title={
                <TooltipText>
                  {
                    "Specifies which twitch width percentages to add to the Per Twitch metrics sheet and Aggregate Metrics sheet."
                  }
                </TooltipText>
              }
            >
              <InfoOutlinedIcon />
            </Tooltip>
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
                handleCheckbox={(checkedBaseline) =>
                  setCheckedBaseline(checkedBaseline)
                }
                checkedState={checkedBaseline}
              />
              Use Baseline Width
            </WALabel>
            {checkedBaseline || <WAOverlay />}
            <ParamContainer>
              <Label htmlFor="baseToPeak">
                Base to Peak:
                <Tooltip
                  title={
                    <TooltipText>
                      {
                        // TODO this needs to be more specific
                        "Specifies the baseline metrics for twitch width percentages."
                      }
                    </TooltipText>
                  }
                >
                  <InfoOutlinedIcon />
                </Tooltip>
              </Label>
              <InputErrorContainer>
                <FormInput
                  name="baseToPeak"
                  placeholder={checkedBaseline ? "10" : ""}
                  value={!checkedBaseline ? "" : inputVals.baseToPeak}
                  onChangeFn={(e) => {
                    updateParams({
                      baseToPeak: e.target.value,
                    });
                  }}
                >
                  <ErrorText id="baseToPeakError" role="errorMsg">
                    {errorMessages.baseToPeak}
                  </ErrorText>
                </FormInput>
              </InputErrorContainer>
            </ParamContainer>
            <ParamContainer>
              <Label htmlFor="peakToBase">
                Peak to Relaxation:
                <Tooltip
                  title={
                    <TooltipText>
                      {
                        // TODO this needs to be more specific
                        "Specifies the baseline metrics for twitch width percentages."
                      }
                    </TooltipText>
                  }
                >
                  <InfoOutlinedIcon />
                </Tooltip>
              </Label>
              <InputErrorContainer>
                <FormInput
                  name="peakToBase"
                  placeholder={checkedBaseline ? "90" : ""}
                  value={!checkedBaseline ? "" : inputVals.peakToBase}
                  onChangeFn={(e) => {
                    updateParams({
                      peakToBase: e.target.value,
                    });
                  }}
                >
                  <ErrorText id="peakToBaseError" role="errorMsg">
                    {errorMessages.peakToBase}
                  </ErrorText>
                </FormInput>
              </InputErrorContainer>
            </ParamContainer>
          </WAOverlayContainer>
        </WindowAnalysisContainer>

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
              <Label htmlFor="startTime">
                Start Time (s):
                <Tooltip
                  title={
                    <TooltipText>
                      {
                        "Specifies the earliest timepoint (in seconds) to use in analysis."
                      }
                    </TooltipText>
                  }
                >
                  <InfoOutlinedIcon />
                </Tooltip>
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
              <Label htmlFor="endTime">
                End Time (s):
                <Tooltip
                  title={
                    <TooltipText>
                      {
                        "Specifies the latest timepoint (in seconds) to use in analysis."
                      }
                    </TooltipText>
                  }
                >
                  <InfoOutlinedIcon />
                </Tooltip>
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
              <Label htmlFor="prominenceFactorPeaks">
                Prominence (µN):
                <Tooltip
                  title={
                    <TooltipText>
                      {
                        "Specifies the minimum required vertical distance between a local max and its lowest contour line to be classified as a peak."
                      }
                    </TooltipText>
                  }
                >
                  <InfoOutlinedIcon />
                </Tooltip>
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
              <Label htmlFor="widthFactorPeaks">
                Width (ms):
                <Tooltip
                  title={
                    <TooltipText>
                      {
                        "Specifies the minimum required width of the base of a local max to be classified as a peak."
                      }
                    </TooltipText>
                  }
                >
                  <InfoOutlinedIcon />
                </Tooltip>
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
