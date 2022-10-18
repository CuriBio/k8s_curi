import styled from "styled-components";
import CheckboxWidget from "../basicWidgets/CheckboxWidget";
import { isArrayOfNumbers } from "../../utils/generic";
import FormInput from "../basicWidgets/FormInput";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";
import { useState, useContext } from "react";
import semverGte from "semver/functions/gte";
import { UploadsContext } from "@/components/layouts/DashboardLayout";

const Container = styled.div`
  padding: 1rem;
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
  flex-direction: row;
  height: 100%;
  justify-content: center;
  width: 420px;
  align-items: center;
`;
const ParamContainer = styled.div`
  display: flex;
  flex-direction: row;
  overflow: visible;
  height: 70px;
  padding: 15px 0 10px 0;
  height: 70px;
  width: 420px;
`;

const InputContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 90%;
`;

const WAOverlay = styled.div`
  border-radius: 5px;
  z-index: 2;
  width: 100%;
  height: 100%;
  background-color: var(--dark-gray);
  opacity: 0.6;
  position: absolute;
  bottom: 0px;
`;
const Label = styled.label`
  width: 110%;
  position: relative;
  height: 25px;
  padding: 10px;
  border-radius: 5px;
  display: flex;
  justify-content: right;
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

const InputErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 70%;
  overflow: visible;
`;

const FormModify = styled.div`
  display: flex;
  width: 162px;
  flex-direction: column;
`;

const SectionLabel = styled.span`
  display: flex;
  align-items: center;
  font-size: 20px;
  position: relative;
  font-weight: bolder;
  margin-top: 20px;
`;

const AdditionalParamLabel = styled.span`
  background-color: var(--light-gray);
  border-radius: 6px;
  position: absolute;
  left: 25%;
  display: flex;
  align-items: center;
  width: 400px;
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

const SmallLabel = styled.label`
  line-height: 2;
  padding-right: 15px;
`;

export default function AnalysisParamForm({
  inputVals,
  errorMessages,
  checkedParams,
  setCheckedParams,
  setAnalysisParams,
  paramErrors,
  setParamErrors,
  analysisParams,
}) {
  const [disableYAxisNormalization, setDisableYAxisNormalization] = useState(false);
  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);

  const pulse3dVersionGte = (version) => {
    const { selectedPulse3dVersion } = inputVals;
    return selectedPulse3dVersion && semverGte(selectedPulse3dVersion, version);
  };

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
      "stiffnessFactor",
    ]) {
      if (paramName in newParams) {
        validatePositiveNumber(updatedParams, paramName, false);
      }
    }
    if (!updatedParams.normalizeYAxis) {
      // if not normalizing y-axis, then clear the entered value.
      // A value can only be entered for max Y if y-axis normalization is enabled
      updatedParams.maxY = "";
    }
    setAnalysisParams(updatedParams);
  };

  const checkPositiveNumberEntry = (value, allowZero = true) => {
    const minValue = allowZero ? 0 : Number.MIN_VALUE;
    return value === null || value === "" || value >= minValue;
  };

  const validatePositiveNumber = (updatedParams, paramName, allowZero = true) => {
    const newValue = updatedParams[paramName];

    let errorMsg = "";
    if (!checkPositiveNumberEntry(newValue, allowZero)) {
      errorMsg = allowZero ? "*Must be a positive number" : "*Must be a positive, non-zero number";
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
      } else {
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
      // both window bounds have a value entered
      updatedParams.startTime &&
      updatedParams.endTime &&
      // neither window bound is invalid individually
      !updatedParamErrors.startTime &&
      !updatedParamErrors.endTime &&
      // bounds do not conflict with each other
      Number(updatedParams.startTime) >= Number(updatedParams.endTime)
    ) {
      updatedParamErrors.endTime = "*Must be greater than Start Time";
    }
    setParamErrors(updatedParamErrors);
  };

  const handleDropDownSelect = (idx) => {
    updateParams({
      selectedPulse3dVersion: pulse3dVersions[idx],
    });
  };

  return (
    <Container>
      <AdditionalParamLabel>
        <CheckboxWidget
          color={"secondary"}
          size={"small"}
          handleCheckbox={(bool) => setCheckedParams(bool)}
          checkedState={checkedParams}
        />
        Use Additional Analysis Parameters
      </AdditionalParamLabel>
      {!checkedParams ? <WAOverlay /> : null}
      <InputContainer>
        <ParamContainer style={{ marginTop: "2%" }}>
          <Label htmlFor="selectedPulse3dVersion" style={{ width: "62%", lineHeight: 2.5 }}>
            Pulse3D Version:
            <Tooltip
              title={
                <TooltipText>
                  {"Specifies which version of the Pulse3D analysis software to use."}
                </TooltipText>
              }
            >
              <InfoOutlinedIcon sx={{ fontSize: 20, margin: "10px 10px" }} />
            </Tooltip>
          </Label>
          <DropDownContainer>
            <DropDownWidget
              options={pulse3dVersions.map((version) => {
                const selectedVersionMeta = metaPulse3dVersions.filter((meta) => meta.version === version);
                return selectedVersionMeta[0] && selectedVersionMeta[0].state === "testing"
                  ? version + " " + "[ testing ]"
                  : version;
              })}
              reset={!checkedParams}
              handleSelection={handleDropDownSelect}
              initialSelected={0}
            />
          </DropDownContainer>
        </ParamContainer>
        {pulse3dVersionGte("0.25.4") && (
          //Disabling y-axis normalization added in version 0.25.4
          <ParamContainer style={{ width: "33%", marginTop: "2%" }}>
            <Label htmlFor="yAxisNormalization">
              Disable Y-Axis Normalization:
              <Tooltip
                title={<TooltipText>{"When selected, disables normalization of the y-axis."}</TooltipText>}
              >
                <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
              </Tooltip>
            </Label>
            <InputErrorContainer>
              <CheckboxWidget
                checkedState={disableYAxisNormalization}
                handleCheckbox={(disable) => {
                  updateParams({
                    normalizeYAxis: !disable,
                  });
                  setDisableYAxisNormalization(disable);
                }}
              />
            </InputErrorContainer>
          </ParamContainer>
        )}
        {pulse3dVersionGte("0.25.0") && (
          // Tanner (9/15/21): maxY added in 0.25.0
          <ParamContainer>
            <Label htmlFor="maxY">
              Y-Axis Range (µN):
              <Tooltip
                title={
                  <TooltipText>
                    {"Specifies the maximum y-axis bound of graphs generated in the output xlsx file."}
                  </TooltipText>
                }
              >
                <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
              </Tooltip>
            </Label>
            <InputErrorContainer>
              <FormInput
                name="maxY"
                placeholder={checkedParams ? "Auto find max y" : ""}
                value={inputVals.maxY}
                onChangeFn={(e) => {
                  updateParams({
                    maxY: e.target.value,
                  });
                }}
                disabled={disableYAxisNormalization}
              >
                <ErrorText id="maxYError" role="errorMsg">
                  {errorMessages.maxY}
                </ErrorText>
              </FormInput>
            </InputErrorContainer>
          </ParamContainer>
        )}
        <ParamContainer>
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
              <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
            </Tooltip>
          </Label>
          <InputErrorContainer>
            <FormInput
              name="twitchWidths"
              placeholder={checkedParams ? "50, 90" : ""}
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
        {pulse3dVersionGte("0.27.0") && (
          // Tanner (9/15/21): stiffnessFactor added in 0.27.0
          <ParamContainer>
            <Label htmlFor="stiffnessFactor">
              Post Stiffness Factor:
              <Tooltip
                title={
                  <TooltipText>
                    {
                      "Specifies the post stiffness factor. If omitted, will use the value encoded in the barcode."
                    }
                  </TooltipText>
                }
              >
                <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
              </Tooltip>
            </Label>
            <InputErrorContainer>
              <FormInput
                name="stiffnessFactor"
                placeholder={checkedParams ? "Auto determine" : ""}
                value={inputVals.stiffnessFactor}
                onChangeFn={(e) => {
                  updateParams({
                    stiffnessFactor: e.target.value,
                  });
                }}
              >
                <ErrorText id="stiffnessFactorError" role="errorMsg">
                  {errorMessages.stiffnessFactor}
                </ErrorText>
              </FormInput>
            </InputErrorContainer>
          </ParamContainer>
        )}

        <SectionLabel>Baseline Width</SectionLabel>

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
              <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
            </Tooltip>
          </Label>
          <InputErrorContainer>
            <FormInput
              name="baseToPeak"
              placeholder={checkedParams ? "10" : ""}
              value={inputVals.baseToPeak}
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
              <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
            </Tooltip>
          </Label>
          <InputErrorContainer>
            <FormInput
              name="peakToBase"
              placeholder={checkedParams ? "90" : ""}
              value={inputVals.peakToBase}
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

        <SectionLabel>Window Analysis</SectionLabel>
        <ParamContainer>
          <Label htmlFor="startTime">
            Start Time (s):
            <Tooltip
              title={
                <TooltipText>
                  {"Specifies the earliest timepoint (in seconds) to use in analysis."}
                </TooltipText>
              }
            >
              <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
            </Tooltip>
          </Label>
          <InputErrorContainer>
            <FormInput
              name="startTime"
              placeholder={checkedParams ? "0" : ""}
              value={inputVals.startTime}
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
                <TooltipText>{"Specifies the latest timepoint (in seconds) to use in analysis."}</TooltipText>
              }
            >
              <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
            </Tooltip>
          </Label>
          <InputErrorContainer>
            <FormInput
              name="endTime"
              placeholder={checkedParams ? "(End of recording)" : ""}
              value={inputVals.endTime}
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

        <SectionLabel>Advanced Analysis</SectionLabel>
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
              <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
            </Tooltip>
          </Label>
          <InputErrorContainer>
            <SmallLabel htmlFor="prominenceFactorPeaks">Peaks</SmallLabel>
            <FormModify>
              <FormInput
                name="prominenceFactorPeaks"
                placeholder={checkedParams ? "6" : ""}
                value={inputVals.prominenceFactorPeaks}
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
            <SmallLabel htmlFor="prominenceFactorValleys">Valleys</SmallLabel>
            <FormModify>
              <FormInput
                name="prominenceFactorValleys"
                placeholder={checkedParams ? "6" : ""}
                value={inputVals.prominenceFactorValleys}
                onChangeFn={(e) => {
                  updateParams({
                    prominenceFactorValleys: e.target.value,
                  });
                }}
              >
                <ErrorText id="prominenceFactorValleysError" role="errorMsg">
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
              <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
            </Tooltip>
          </Label>
          <InputErrorContainer>
            <SmallLabel htmlFor="widthFactorPeaks">Peaks</SmallLabel>
            <FormModify>
              <FormInput
                name="widthFactorPeaks"
                placeholder={checkedParams ? "7" : ""}
                value={inputVals.widthFactorPeaks}
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
            <SmallLabel htmlFor="widthFactorValleys">Valleys</SmallLabel>
            <FormModify>
              <FormInput
                name="widthFactorValleys"
                placeholder={checkedParams ? "7" : ""}
                value={inputVals.widthFactorValleys}
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
      </InputContainer>
    </Container>
  );
}
