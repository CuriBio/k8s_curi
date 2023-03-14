import styled from "styled-components";
import CheckboxWidget from "../basicWidgets/CheckboxWidget";
import { isArrayOfNumbers, loadCsvInputToArray, isArrayOfWellNames } from "../../utils/generic";
import FormInput from "../basicWidgets/FormInput";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";
import { useState, useContext } from "react";
import semverGte from "semver/functions/gte";
import { UploadsContext } from "@/components/layouts/DashboardLayout";
import WellGroups from "@/components/uploadForm/WellGroups";

const Container = styled.div`
  padding: 1rem;
  left: 5%;
  top: 12%;
  width: 90%;
  position: relative;
  display: grid;
  border: solid;
  justify-content: center;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 7px;
  background-color: var(--light-gray);
  margin-top: 8%;
  margin-bottom: 4;
  grid-template-columns: 45% 55%;
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
  display: grid;
  grid-template-columns: 60% 50%;
  height: 70px;
  padding: 15px 0 10px 0;
  height: 70px;
  width: 380px;
`;

const InputContainerOne = styled.div`
  display: flex;
  flex-direction: column;
  align-items: start;
  border-right: 1px solid var(--dark-gray);
`;

const InputContainerTwo = styled.div`
  display: flex;
  flex-direction: column;
  align-items: start;
  padding-left: 20px;
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

const InputErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 70%;
  height: 60px;
`;

const FormModify = styled.div`
  display: flex;
  width: 90px;
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
  width: 57%;
  height: 99%;
  background: white;
  border-radius: 5px;
`;

const SmallLabel = styled.label`
  line-height: 2;
  padding-right: 15px;
`;

const AdvAnalysisContainer = styled.div`
display: flex;
flex-direction row;
height: 157px;
`;

export default function AnalysisParamForm({
  errorMessages,
  checkedParams,
  setCheckedParams,
  setAnalysisParams,
  paramErrors,
  setParamErrors,
  analysisParams,
  setWellGroupErr,
}) {
  const [disableYAxisNormalization, setDisableYAxisNormalization] = useState(false);
  const [disableStimProtocols, setDisableStimProtocols] = useState(false);
  const { pulse3dVersions, metaPulse3dVersions, stiffnessFactorDetails } = useContext(UploadsContext);

  const pulse3dVersionGte = (version) => {
    const { selectedPulse3dVersion } = analysisParams;
    return selectedPulse3dVersion && semverGte(selectedPulse3dVersion, version);
  };

  const stimWaveformFormatDetails = {
    Stacked: "stacked",
    Overlayed: "overlayed",
    None: null,
  };

  const updateParams = (newParams) => {
    const updatedParams = { ...analysisParams, ...newParams };

    if ("twitchWidths" in newParams) {
      validateTwitchWidths(updatedParams);
    }

    if ("wellsWithFlippedWaveforms" in newParams) {
      validateWellNames(updatedParams);
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
      if (paramName in newParams) validatePositiveNumber(updatedParams, paramName, false);
    }

    if (newParams.normalizeYAxis === false) {
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
      // make sure it's a valid array
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

  const validateWellNames = (updatedParams) => {
    const newValue = updatedParams.wellsWithFlippedWaveforms;
    let formattedWellNames;
    if (newValue === null || newValue === "") {
      formattedWellNames = "";
    } else {
      // load into an array
      let wellNameArr = loadCsvInputToArray(newValue);
      // make sure it's an array of valid well names
      if (isArrayOfWellNames(wellNameArr, true)) {
        formattedWellNames = Array.from(new Set(wellNameArr));
      } else {
        setParamErrors({
          ...paramErrors,
          wellsWithFlippedWaveforms: "*Must be comma-separated Well Names (i.e. A1, D6)",
        });
        return;
      }
    }
    setParamErrors({ ...paramErrors, wellsWithFlippedWaveforms: "" });
    updatedParams.wellsWithFlippedWaveforms = formattedWellNames;
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

  return (
    <Container>
      <AdditionalParamLabel
        style={checkedParams ? { background: "white" } : { background: "var(--light-gray)" }}
      >
        <CheckboxWidget
          color={"secondary"}
          size={"small"}
          handleCheckbox={(bool) => setCheckedParams(bool)}
          checkedState={checkedParams}
        />
        Use Additional Analysis Parameters
      </AdditionalParamLabel>
      {!checkedParams ? <WAOverlay /> : null}
      <InputContainerOne>
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
              handleSelection={(idx) => {
                updateParams({
                  selectedPulse3dVersion: pulse3dVersions[idx],
                });
              }}
              initialSelected={0}
            />
          </DropDownContainer>
        </ParamContainer>

        {pulse3dVersionGte("0.30.5") && (
          <ParamContainer>
            <Label
              htmlFor="stimWaveformFormat"
              style={{
                width: "102%",
                lineHeight: 1.5,
                "white-space": "normal",
                "text-align": "center",
              }}
            >
              Stim Waveform Display Format:
              <Tooltip
                title={
                  <TooltipText>
                    {"Specifies the display format for the stim waveforms (if any). Defaults to 'Stacked'"}
                  </TooltipText>
                }
              >
                <InfoOutlinedIcon sx={{ fontSize: 20, margin: "10px 10px" }} />
              </Tooltip>
            </Label>
            <DropDownContainer>
              <DropDownWidget
                options={Object.keys(stimWaveformFormatDetails)}
                reset={!checkedParams}
                handleSelection={(idx) => {
                  updateParams({
                    stimWaveformFormat: Object.values(stimWaveformFormatDetails)[idx],
                  });
                }}
                initialSelected={0}
              />
            </DropDownContainer>
          </ParamContainer>
        )}

        {pulse3dVersionGte("0.28.1") && (
          <ParamContainer>
            <Label htmlFor="showStimSheet">
              Show Stimulation Protocols:
              <Tooltip
                title={
                  <TooltipText>
                    {"When selected, adds a sheet to output file with stimulation protocols."}
                  </TooltipText>
                }
              >
                <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
              </Tooltip>
            </Label>
            <InputErrorContainer style={{ marginLeft: "20%" }}>
              <CheckboxWidget
                checkedState={disableStimProtocols}
                handleCheckbox={() => {
                  setDisableStimProtocols(!disableStimProtocols);
                  updateParams({
                    showStimSheet: !disableStimProtocols,
                  });
                }}
              />
            </InputErrorContainer>
          </ParamContainer>
        )}

        {pulse3dVersionGte("0.25.4") && (
          //Disabling y-axis normalization added in version 0.25.4
          <ParamContainer>
            <Label htmlFor="normalizeYAxis">
              Disable Y-Axis Normalization:
              <Tooltip
                title={<TooltipText>{"When selected, disables normalization of the y-axis."}</TooltipText>}
              >
                <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
              </Tooltip>
            </Label>
            <InputErrorContainer style={{ marginLeft: "20%" }}>
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
                value={analysisParams.maxY}
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
              value={analysisParams.twitchWidths}
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
        {pulse3dVersionGte("0.30.1") && (
          // Tanner (2/7/23): stiffnessFactor added in 0.26.0 but there are bugs with using this param in re-analysis prior to 0.30.1
          <ParamContainer>
            <Label htmlFor="stiffnessFactor" style={{ width: "62%", lineHeight: 2.5 }}>
              Post Stiffness Factor:
              <Tooltip
                title={
                  <TooltipText>
                    {
                      "Specifies the post stiffness factor. If set to 'auto', will use the value encoded in the barcode."
                    }
                  </TooltipText>
                }
              >
                <InfoOutlinedIcon sx={{ fontSize: 20, margin: "10px 10px" }} />
              </Tooltip>
            </Label>
            <DropDownContainer>
              <DropDownWidget
                options={Object.keys(stiffnessFactorDetails)}
                reset={!checkedParams}
                handleSelection={(idx) => {
                  updateParams({
                    stiffnessFactor: Object.values(stiffnessFactorDetails)[idx],
                  });
                }}
                initialSelected={0}
              />
            </DropDownContainer>
          </ParamContainer>
        )}
        {pulse3dVersionGte("0.30.1") && (
          // Tanner (2/7/23): wellsWithFlippedWaveforms added in 0.27.4 but there are bugs with using this param in re-analysis prior to 0.30.1
          <ParamContainer style={{ padding: "20px 0px 10px 0px", width: "500px" }}>
            <Label htmlFor="wellsWithFlippedWaveforms">
              Wells With Flipped Waveforms:
              <Tooltip
                title={
                  <TooltipText>
                    {
                      "[Beta 1.7 Instrument Recordings Only] Specifies the names of wells (i.e. A1, D6) which should have their waveforms flipped before analysis begins."
                    }
                  </TooltipText>
                }
              >
                <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
              </Tooltip>
            </Label>
            <InputErrorContainer>
              <FormInput
                name="wellsWithFlippedWaveforms"
                placeholder={checkedParams ? "None" : ""}
                value={analysisParams.wellsWithFlippedWaveforms}
                onChangeFn={(e) => {
                  updateParams({
                    wellsWithFlippedWaveforms: e.target.value,
                  });
                }}
              >
                <ErrorText id="twitchWidthError" role="errorMsg" style={{ width: "110%" }}>
                  {errorMessages.wellsWithFlippedWaveforms}
                </ErrorText>
              </FormInput>
            </InputErrorContainer>
          </ParamContainer>
        )}
      </InputContainerOne>
      <InputContainerTwo>
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
              value={analysisParams.baseToPeak}
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
              value={analysisParams.peakToBase}
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
              value={analysisParams.startTime}
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
              value={analysisParams.endTime}
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
        <AdvAnalysisContainer>
          <TwoParamContainer style={{ width: "300px", alignItems: "start" }}>
            <Label htmlFor="prominenceFactorPeaks" style={{ padding: "25px" }}>
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
            <InputErrorContainer style={{ height: "100px" }}>
              <SmallLabel htmlFor="prominenceFactorPeaks">Peaks</SmallLabel>
              <FormModify>
                <FormInput
                  name="prominenceFactorPeaks"
                  placeholder={checkedParams ? "6" : ""}
                  value={analysisParams.prominenceFactorPeaks}
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
                  value={analysisParams.prominenceFactorValleys}
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
          <TwoParamContainer style={{ alignItems: "start" }}>
            <Label htmlFor="widthFactorPeaks" style={{ padding: "25px" }}>
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
            <InputErrorContainer style={{ height: "100px" }}>
              <SmallLabel htmlFor="widthFactorPeaks">Peaks</SmallLabel>
              <FormModify>
                <FormInput
                  name="widthFactorPeaks"
                  placeholder={checkedParams ? "7" : ""}
                  value={analysisParams.widthFactorPeaks}
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
                  value={analysisParams.widthFactorValleys}
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
        </AdvAnalysisContainer>
        {pulse3dVersionGte("0.30.3") && (
          <WellGroups
            setAnalysisParams={setAnalysisParams}
            analysisParams={analysisParams}
            setWellGroupErr={setWellGroupErr}
          />
        )}
      </InputContainerTwo>
    </Container>
  );
}
