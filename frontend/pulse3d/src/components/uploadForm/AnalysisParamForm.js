import styled from "styled-components";
import CheckboxWidget from "@/components/basicWidgets/CheckboxWidget";
import { isArrayOfNumbers, loadCsvInputToArray, isArrayOfWellNames } from "../../utils/generic";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import { useState, useContext, useEffect } from "react";
import semverGte from "semver/functions/gte";
import { UploadsContext } from "@/components/layouts/DashboardLayout";
import WellGroups from "@/components/uploadForm/WellGroups";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import AnalysisParamContainer from "@/components/uploadForm/AnalysisParamContainer";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";
import FormInput from "@/components/basicWidgets/FormInput";

const Container = styled.div`
  padding: 1rem;
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
  reanalysis,
  xlsxFilePresent,
}) {
  const [disableYAxisNormalization, setDisableYAxisNormalization] = useState(false);
  const [disableStimProtocols, setDisableStimProtocols] = useState(false);
  const { pulse3dVersions, metaPulse3dVersions, stiffnessFactorDetails } = useContext(UploadsContext);
  const [deprecationNotice, setDeprecationNotice] = useState(false);
  const [pulse3dVersionEOLDate, setPulse3dVersionEOLDate] = useState("");
  const [pulse3dVersionOptions, setPulse3dVersionOptions] = useState([]);

  const handlePulse3dVersionSelect = (idx) => {
    const selectedVersionMetadata = metaPulse3dVersions.filter(
      (version) => version.version === pulse3dVersions[idx]
    )[0];
    if (selectedVersionMetadata) {
      let warning = `Version ${selectedVersionMetadata.version} will be removed `;
      warning += selectedVersionMetadata.end_of_life_date
        ? `after ${selectedVersionMetadata.end_of_life_date}.`
        : "soon.";
      setPulse3dVersionEOLDate(warning);
      setDeprecationNotice(selectedVersionMetadata.state === "deprecated");
    }
    updateParams({
      selectedPulse3dVersion: pulse3dVersions[idx],
    });
  };

  useEffect(() => {
    const filteredOptions = pulse3dVersions.filter(
      (version) => !xlsxFilePresent || semverGte(version, "0.32.2")
    );
    const options = filteredOptions.map((version) => {
      const selectedVersionMeta = metaPulse3dVersions.filter((meta) => meta.version === version);
      if (selectedVersionMeta[0] && ["testing", "deprecated"].includes(selectedVersionMeta[0].state)) {
        return version + `  [ ${selectedVersionMeta[0].state} ]`;
      } else {
        return version;
      }
    });

    setPulse3dVersionOptions([...options]);
  }, [pulse3dVersions, metaPulse3dVersions, xlsxFilePresent]);

  const pulse3dVersionGte = (version) => {
    const { selectedPulse3dVersion } = analysisParams;
    return selectedPulse3dVersion && semverGte(selectedPulse3dVersion, version);
  };

  const stimWaveformFormatDetails = {
    None: null,
    Stacked: "stacked",
    Overlayed: "overlayed",
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
      <InputContainerOne style={{ paddingTop: "2%" }}>
        {pulse3dVersionGte("0.32.2") && reanalysis && (
          <AnalysisParamContainer
            label="Override original name"
            name="nameOverride"
            tooltipText="This name will replace the original recording name for the ouput filename."
            additionaErrorStyle={{ width: "150%" }}
            placeholder=""
            value={analysisParams.nameOverride}
            changeFn={(e) => {
              updateParams({
                nameOverride: e.target.value,
              });
            }}
            errorMsg={errorMessages.nameOverride}
          />
        )}
        <AnalysisParamContainer
          label="Pulse3D Version"
          name="selectedPulse3dVersion"
          tooltipText="Specifies which version of the Pulse3D analysis software to use."
          additionalLabelStyle={{ width: "62%", lineHeight: 2.5 }}
          iconStyle={{ fontSize: 20, margin: "10px 10px" }}
        >
          <DropDownContainer>
            <DropDownWidget
              options={pulse3dVersionOptions}
              reset={!checkedParams}
              handleSelection={handlePulse3dVersionSelect}
              initialSelected={0}
            />
          </DropDownContainer>
        </AnalysisParamContainer>
        {pulse3dVersionGte("0.30.5") && (
          <AnalysisParamContainer
            label="Stim Waveform Display Format"
            name="stimWaveformFormat"
            tooltipText="Specifies the display format for the stim waveforms (if any). Defaults to 'Stacked'"
            additionalLabelStyle={{
              width: "102%",
              lineHeight: 1.5,
              whiteSpace: "normal",
              textAlign: "center",
            }}
            iconStyle={{ fontSize: 20, margin: "10px 10px" }}
          >
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
          </AnalysisParamContainer>
        )}

        <AnalysisParamContainer
          label="Show Stimulation Protocols"
          name="showStimSheet"
          tooltipText="When selected, adds a sheet to output file with stimulation protocols."
        >
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
        </AnalysisParamContainer>
        <AnalysisParamContainer
          label="Disable Y-Axis Normalization:"
          name="normalizeYAxis"
          tooltipText="When selected, disables normalization of the y-axis."
        >
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
        </AnalysisParamContainer>
        <AnalysisParamContainer
          label="Y-Axis Range (µN)"
          name="maxY"
          tooltipText="Specifies the maximum y-axis bound of graphs generated in the output xlsx file."
          placeholder={checkedParams ? "Auto" : ""}
          value={analysisParams.maxY}
          changeFn={(e) => {
            updateParams({
              maxY: e.target.value,
            });
          }}
          disabled={disableYAxisNormalization}
          errorMsg={errorMessages.maxY}
        />
        <AnalysisParamContainer
          label="Twitch Widths (%)"
          name="twitchWidths"
          tooltipText="Specifies which twitch width percentages to add to the Per Twitch metrics sheet and Aggregate Metrics sheet."
          placeholder={checkedParams ? "50, 90" : ""}
          value={analysisParams.twitchWidths}
          changeFn={(e) => {
            updateParams({
              twitchWidths: e.target.value,
            });
          }}
          errorMsg={errorMessages.twitchWidths}
        />
        {pulse3dVersionGte("0.30.1") && (
          // Tanner (2/7/23): stiffnessFactor added in 0.26.0 but there are bugs with using this param in re-analysis prior to 0.30.1
          <AnalysisParamContainer
            label="Post Stiffness Factor"
            name="stiffnessFactor"
            tooltipText="Specifies the post stiffness factor. If set to 'auto', will use the value encoded in the barcode."
            additionaLabelStyle={{ width: "62%", lineHeight: 2.5 }}
            iconStyle={{ fontSize: 20, margin: "10px 10px" }}
          >
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
          </AnalysisParamContainer>
        )}
        {pulse3dVersionGte("0.30.1") && (
          // Tanner (2/7/23): wellsWithFlippedWaveforms added in 0.27.4 but there are bugs with using this param in re-analysis prior to 0.30.1
          <AnalysisParamContainer
            label="Wells With Flipped Waveforms"
            name="wellsWithFlippedWaveforms"
            tooltipText="[Beta 1.7 Instrument Recordings Only] Specifies the names of wells (i.e. A1, D6) which should have their waveforms flipped before analysis begins."
            placeholder={checkedParams ? "None" : ""}
            value={analysisParams.wellsWithFlippedWaveforms}
            additionalErrorStyle={{ width: "50%" }}
            changeFn={(e) => {
              updateParams({
                wellsWithFlippedWaveforms: e.target.value,
              });
            }}
            additionalParamStyle={{
              padding: "20px 0px 10px 0px",
              width: "500px",
            }}
            errorMsg={errorMessages.wellsWithFlippedWaveforms}
          />
        )}
      </InputContainerOne>
      <InputContainerTwo>
        <SectionLabel>Baseline Width</SectionLabel>
        <AnalysisParamContainer
          label="Base to Peak"
          name="baseToPeak"
          tooltipText="Specifies the baseline metrics for twitch width percentages."
          placeholder={checkedParams ? "10" : ""}
          value={analysisParams.baseToPeak}
          changeFn={(e) => {
            updateParams({
              baseToPeak: e.target.value,
            });
          }}
          errorMsg={errorMessages.baseToPeak}
        />
        <AnalysisParamContainer
          label="Peak to Relaxation"
          name="peakToBase"
          tooltipText="Specifies the baseline metrics for twitch width percentages."
          placeholder={checkedParams ? "90" : ""}
          value={analysisParams.peakToBase}
          changeFn={(e) => {
            updateParams({
              peakToBase: e.target.value,
            });
          }}
          errorMsg={errorMessages.peakToBase}
        />
        <SectionLabel>Window Analysis</SectionLabel>
        <AnalysisParamContainer
          label="Start Time (s)"
          name="startTime"
          tooltipText="Specifies the earliest timepoint (in seconds) to use in analysis."
          placeholder={checkedParams ? "0" : ""}
          value={analysisParams.startTime}
          changeFn={(e) => {
            updateParams({
              startTime: e.target.value,
            });
          }}
          errorMsg={errorMessages.startTime}
        />
        <AnalysisParamContainer
          label="End Time (s)"
          name="endTime"
          tooltipText="Specifies the latest timepoint (in seconds) to use in analysis."
          placeholder={checkedParams ? "End" : ""}
          value={analysisParams.endTime}
          changeFn={(e) => {
            updateParams({
              endTime: e.target.value,
            });
          }}
          errorMsg={errorMessages.endTime}
        />
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
      <ModalWidget
        open={deprecationNotice}
        labels={[pulse3dVersionEOLDate]}
        closeModal={() => {
          setDeprecationNotice(false);
        }}
        header={"Attention!"}
      />
    </Container>
  );
}
