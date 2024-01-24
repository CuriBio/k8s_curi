import styled from "styled-components";
import CheckboxWidget from "@/components/basicWidgets/CheckboxWidget";
import { isArrayOfNumbers, loadCsvInputToArray, isArrayOfWellNames, isInt } from "@/utils/generic";
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
import { AuthContext } from "@/pages/_app";

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
  height: 74px;
  justify-content: left;
  width: 124%;
  align-items: center;
`;

const AdditionalParamLabel = styled.div`
  width: 300px;
`;

const PresetDropdownContainer = styled.div`
  width: 450px;
  padding: 0 40px;
  display: flex;
  flex-direction: row;
  font-size: 13px;
  font-style: italic;
  white-space: nowrap;
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
  height: 60px;
  margin-left: 20%;
`;

const TwoInputErrorContainer = styled.div`
  height: 100px;
  display: flex;
  flex-direction: row;
  align-items: center;
`;

const FormModify = styled.div`
  display: flex;
  width: 90px;
  height: 54px;
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

const AdditionalParamLabelContainer = styled.span`
  background-color: var(--light-gray);
  border-radius: 6px;
  position: absolute;
  left: 25%;
  display: flex;
  align-items: center;
  font-size: 17px;
  z-index: 3;
  border: 2px solid var(--dark-gray);
  cursor: default;
  height: 65px;
  justify-content: center;
  top: -45px;
  left: 5%;
  font-weight: 900;
`;

const TooltipText = styled.span`
  font-size: 15px;
`;

const DropDownContainer = styled.div`
  width: 57%;
  height: 89%;
  background: white;
  border-radius: 5px;
`;

const SmallLabel = styled.label`
  line-height: 2;
  padding-right: 15px;
`;

const OriginalAdvAnalysisContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 77%;
  height: 157px;
`;

const NoiseBasedAdvAnalysisContainer = styled.div`
  display: flex;
  flex-direction: column;
`;

const LineSeparator = styled.hr`
  height: 1px;
  border: 0;
  border-top: 1px solid var(--dark-gray);
  padding: 0;
  position: relative;
  width: 100%;
`;

function OrginalPeakFindingAdvAnalysisParams({ analysisParams, checkedParams, updateParams, errorMessages }) {
  return (
    <>
      <TwoParamContainer>
        <Label htmlFor="prominenceFactors" style={{ padding: "0px 36px 0 10px" }}>
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
        <TwoInputErrorContainer>
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
        </TwoInputErrorContainer>
      </TwoParamContainer>
      <TwoParamContainer style={{ width: "134%" }}>
        <Label htmlFor="widthFactorPeaks" style={{ padding: "0px 76px 0 10px" }}>
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
        <TwoInputErrorContainer>
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
        </TwoInputErrorContainer>
      </TwoParamContainer>
    </>
  );
}

function NoiseBasedPeakFindingAdvAnalysisParams({
  analysisParams,
  checkedParams,
  updateParams,
  errorMessages,
}) {
  return (
    <>
      <AnalysisParamContainer
        label="Noise Prominence Factor"
        name="noiseProminenceFactor"
        tooltipText="Specifies the minimum required signal-to-noise ratio of peaks."
        additionaErrorStyle={{ width: "150%" }}
        placeholder={checkedParams ? "2.5" : ""}
        value={analysisParams.noiseProminenceFactor}
        changeFn={(e) => {
          updateParams({
            noiseProminenceFactor: e.target.value,
          });
        }}
        errorMsg={errorMessages.noiseProminenceFactor}
      />
      <AnalysisParamContainer
        label="Relative Prominence Factor"
        name="relativeProminenceFactor"
        tooltipText="Specifies the minimum required percentage of peak amplitude relative to the tallest peak."
        additionaErrorStyle={{ width: "150%" }}
        placeholder={checkedParams ? "0.2" : ""}
        value={analysisParams.relativeProminenceFactor}
        changeFn={(e) => {
          updateParams({
            relativeProminenceFactor: e.target.value,
          });
        }}
        errorMsg={errorMessages.relativeProminenceFactor}
      />
      {/* TODO make sure to convert everything from ms to seconds before sending in the route */}
      <TwoParamContainer>
        <Label htmlFor="minPeakWidth" style={{ padding: "0px 92px 0 10px" }}>
          Width (ms):
          <Tooltip
            title={<TooltipText>{"Specifies the min and max width requirements for peaks."}</TooltipText>}
          >
            <InfoOutlinedIcon sx={{ fontSize: 20, margin: "0px 10px" }} />
          </Tooltip>
        </Label>
        <TwoInputErrorContainer>
          <SmallLabel htmlFor="minPeakWidth">Min</SmallLabel>
          <FormModify>
            <FormInput
              name="minPeakWidth"
              placeholder={checkedParams ? "0" : ""}
              value={analysisParams.minPeakWidth}
              onChangeFn={(e) => {
                updateParams({
                  minPeakWidth: e.target.value,
                });
              }}
            >
              <ErrorText id="minPeakWidthError" role="errorMsg">
                {errorMessages.minPeakWidth}
              </ErrorText>
            </FormInput>
          </FormModify>
          <SmallLabel htmlFor="maxPeakWidth">Max</SmallLabel>
          <FormModify>
            <FormInput
              name="maxPeakWidth"
              placeholder={checkedParams ? "5000" : ""}
              value={analysisParams.maxPeakWidth}
              onChangeFn={(e) => {
                updateParams({
                  maxPeakWidth: e.target.value,
                });
              }}
            >
              <ErrorText id="maxPeakWidthError" role="errorMsg">
                {errorMessages.maxPeakWidth}
              </ErrorText>
            </FormInput>
          </FormModify>
        </TwoInputErrorContainer>
      </TwoParamContainer>
      <AnalysisParamContainer
        label="Min Peak Height (µN)"
        name="minPeakHeight"
        tooltipText="Specifies the minimum required height of peaks."
        additionaErrorStyle={{ width: "150%" }}
        placeholder={checkedParams ? "0" : ""}
        value={analysisParams.minPeakHeight}
        changeFn={(e) => {
          updateParams({
            minPeakHeight: e.target.value,
          });
        }}
        errorMsg={errorMessages.minPeakHeight}
      />
      <AnalysisParamContainer
        label="Max Frequency of Peaks (Hz)"
        name="maxPeakFreq"
        tooltipText="Specifies the maximum frequency at which peaks can occur."
        additionaErrorStyle={{ width: "150%" }}
        placeholder={checkedParams ? "100" : ""}
        value={analysisParams.maxPeakFreq}
        changeFn={(e) => {
          updateParams({
            maxPeakFreq: e.target.value,
          });
        }}
        errorMsg={errorMessages.maxPeakFreq}
      />
      <AnalysisParamContainer
        label="Valley Window (ms)"
        name="valleySearchDuration"
        tooltipText="Specifies the duration of time prior to a peak in which a valley can be located."
        additionaErrorStyle={{ width: "150%" }}
        placeholder={checkedParams ? "1000" : ""}
        value={analysisParams.valleySearchDuration}
        changeFn={(e) => {
          updateParams({
            valleySearchDuration: e.target.value,
          });
        }}
        errorMsg={errorMessages.valleySearchDuration}
      />
      <AnalysisParamContainer
        label="Valley Upslope Duration (ms)"
        name="upslopeDuration"
        tooltipText="Specifies the min duration of time through which the waveform amplitude must continuously rise in order to be considered an upslope."
        additionaErrorStyle={{ width: "150%" }}
        placeholder={checkedParams ? "70" : ""}
        value={analysisParams.upslopeDuration}
        changeFn={(e) => {
          updateParams({
            upslopeDuration: e.target.value,
          });
        }}
        errorMsg={errorMessages.upslopeDuration}
      />
      <AnalysisParamContainer
        label="Valley Upslope Noise Allowance (ms)"
        name="upslopeNoiseAllowance"
        tooltipText="Specifies the max duration of time in which there is an amplitude decrease which can be tolerated within a single upslope."
        additionaErrorStyle={{ width: "150%" }}
        placeholder={checkedParams ? "10" : ""}
        value={analysisParams.upslopeNoiseAllowance}
        changeFn={(e) => {
          updateParams({
            upslopeNoiseAllowance: e.target.value,
          });
        }}
        errorMsg={errorMessages.upslopeNoiseAllowance}
        additionalLabelStyle={{
          width: "102%",
          whiteSpace: "normal",
        }}
      />
    </>
  );
}

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
  userPresetOpts: {
    userPresets,
    setSelectedPresetIdx,
    savePresetChecked,
    setSavePresetChecked,
    setAnalysisPresetName,
    analysisPresetName,
  },
}) {
  const { pulse3dVersions, metaPulse3dVersions, stiffnessFactorDetails, dataTypeDetails } = useContext(
    UploadsContext
  );
  const { preferences, productPage } = useContext(AuthContext);

  const [disableYAxisNormalization, setDisableYAxisNormalization] = useState(false);
  const [disableStimProtocols, setDisableStimProtocols] = useState(false);
  const [deprecationNotice, setDeprecationNotice] = useState(false);
  const [pulse3dVersionEOLDateWarning, setPulse3dVersionEOLDateWarning] = useState("");
  const [pulse3dVersionOptions, setPulse3dVersionOptions] = useState([]);
  const [pulse3dFilteredFileVersions, setPulse3dFilteredFileVersions] = useState([]);

  const handlePulse3dVersionSelect = (idx) => {
    const selectedVersionMetadata = metaPulse3dVersions.find(
      (version) => version.version === pulse3dFilteredFileVersions[idx]
    );

    if (selectedVersionMetadata) {
      let warning = `Version ${selectedVersionMetadata.version} will be removed `;
      warning += selectedVersionMetadata.end_of_life_date
        ? `after ${selectedVersionMetadata.end_of_life_date}.`
        : "soon.";
      // TODO try refactoring this so it just opens if a warning is set
      setPulse3dVersionEOLDateWarning(warning);
      setDeprecationNotice(selectedVersionMetadata.state === "deprecated");
    }

    updateParams({
      selectedPulse3dVersion: pulse3dFilteredFileVersions[idx],
    });
  };

  useEffect(() => {
    // set back to initial version index, this gets handled after a file is uploaded and if an xlsx file is present, the pulse3d versions will be in a different order.
    updateParams({
      selectedPulse3dVersion:
        pulse3dFilteredFileVersions[
          getDropdownInitialSelection("selectedPulse3dVersion", pulse3dFilteredFileVersions)
        ],
    });

    const options = pulse3dFilteredFileVersions.map((version) => {
      const selectedVersionMeta = metaPulse3dVersions.filter((meta) => meta.version === version);
      return selectedVersionMeta[0] && ["testing", "deprecated"].includes(selectedVersionMeta[0].state)
        ? version + `  [ ${selectedVersionMeta[0].state} ]`
        : version;
    });

    setPulse3dVersionOptions([...options]);
  }, [pulse3dFilteredFileVersions, metaPulse3dVersions]);

  useEffect(() => {
    // default gets set to empty string
    setDisableYAxisNormalization(
      analysisParams.normalizeYAxis !== "" ? !analysisParams.normalizeYAxis : false
    );
  }, [analysisParams.normalizeYAxis, checkedParams]);

  useEffect(() => {
    // default gets set to empty string
    setDisableStimProtocols(analysisParams.showStimSheet !== "" ? analysisParams.showStimSheet : false);
  }, [analysisParams.showStimSheet, checkedParams]);

  useEffect(() => {
    const filteredOptions = pulse3dVersions.filter((version) => {
      if (!xlsxFilePresent) return true;

      const minVersion = xlsxFilePresent <= 24 ? "0.32.2" : "0.33.13";
      return semverGte(version, minVersion);
    });

    setPulse3dFilteredFileVersions([...filteredOptions]);
  }, [pulse3dVersions, xlsxFilePresent]);

  const pulse3dVersionGte = (version) => {
    const { selectedPulse3dVersion } = analysisParams;
    return selectedPulse3dVersion && semverGte(selectedPulse3dVersion, version);
  };

  const useNoiseBasedPeakFinding = () => {
    return pulse3dVersionGte("0.33.2");
  };

  const stimWaveformFormatDetails = {
    None: null,
    Stacked: "stacked",
    Overlayed: "overlayed",
  };

  const nautilaiNormalizationMethods = ["None", "F/Fmin", "∆F/Fmin"];

  const getDropdownInitialSelection = (param, optionsArr) => {
    let optionIndex = optionsArr.indexOf(analysisParams[param]);

    // set initial p3d version to user preference if available, account for it to now always be set
    // additionally, need to wait for pulse3dVersions to be fetched and set
    if (
      param == "selectedPulse3dVersion" &&
      productPage in preferences &&
      "version" in preferences[productPage] &&
      pulse3dVersions.length > 0
    ) {
      optionIndex = optionsArr.indexOf(preferences[productPage].version);
    }

    return optionIndex === -1 ? 0 : optionIndex;
  };

  const updateParams = (newParams) => {
    const updatedParams = { ...analysisParams, ...newParams };

    if ("twitchWidths" in newParams) {
      validateTwitchWidths(updatedParams);
    }

    if ("wellsWithFlippedWaveforms" in newParams) {
      validateWellNames(updatedParams);
    }

    let updatedParamErrors = { ...paramErrors };
    for (const [minName, maxName] of [
      ["startTime", "endTime"],
      ["minPeakWidth", "maxPeakWidth"],
    ]) {
      if (minName in newParams || maxName in newParams) {
        // need to validate start and end time together
        const allowFloat = minName === "startTime";
        const newParamErrors = validateMinMax(updatedParams, minName, maxName, allowFloat);
        updatedParamErrors = { ...updatedParamErrors, ...newParamErrors };
      }
    }

    for (const paramName of [
      "prominenceFactorPeaks",
      "prominenceFactorValleys",
      "widthFactorPeaks",
      "widthFactorValleys",
      "noiseProminenceFactor",
      "relativeProminenceFactor",
      "minPeakHeight",
      "maxPeakFreq",
      "valleySearchDuration",
      "upslopeDuration",
      "upslopeNoiseAllowance",
      "maxY",
      "baseToPeak",
      "peakToBase",
      "stiffnessFactor",
    ]) {
      const allowFloat = !["baseToPeak", "peakToBase"].includes(paramName);
      if (paramName in newParams) {
        const newParamErrors = validatePositiveNumber(updatedParams, paramName, false, allowFloat);
        updatedParamErrors = { ...updatedParamErrors, ...newParamErrors };
      }
    }
    setParamErrors(updatedParamErrors);

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

  const validatePositiveNumber = (updatedParams, paramName, allowZero = true, allowFloat = true) => {
    const newValue = updatedParams[paramName];

    let errorMsg = "";
    if (!checkPositiveNumberEntry(newValue, allowZero) || (!allowFloat && !isInt(newValue))) {
      errorMsg = `*Must be a positive${allowZero ? "" : ", non-zero"} ${allowFloat ? "number" : "integer"}`;
    }
    return { [paramName]: errorMsg };
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
          twitchWidths: "*Must be comma-separated, positive integers",
        });
        return;
      }
      // make sure it's an array of positive integers
      if (isArrayOfNumbers(twitchWidthArr, true, false)) {
        formattedTwitchWidths = Array.from(new Set(twitchWidthArr));
      } else {
        setParamErrors({
          ...paramErrors,
          twitchWidths: "*Must be comma-separated, positive integers",
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

  const validatePresetName = (input) => {
    const nameFound = userPresets.map(({ name }) => name).find((name) => name === input);

    let errorMessage = "";
    if (nameFound) errorMessage = "*Name already exists";
    else if (input === "" && savePresetChecked) errorMessage = "*Required";

    setAnalysisPresetName(input);
    setParamErrors({ ...paramErrors, presetName: errorMessage });
  };

  const validateMinMax = (updatedParams, minName, maxName, allowFloat) => {
    const minValue = updatedParams[minName];
    const maxValue = updatedParams[maxName];

    let updatedParamErrors = { ...paramErrors };
    for (const [boundName, boundValue] of [
      [minName, minValue],
      [maxName, maxValue],
    ]) {
      // only perform this check if something has actually been entered
      if (boundValue) {
        const allowZero = boundName === minName;
        const newParamErrors = validatePositiveNumber(updatedParams, boundName, allowZero, allowFloat);
        updatedParamErrors = { ...updatedParamErrors, ...newParamErrors };
      }
    }

    if (
      // both bounds have a value entered
      updatedParams[minName] &&
      updatedParams[maxName] &&
      // neither bound is invalid individually
      !updatedParamErrors[minName] &&
      !updatedParamErrors[maxName] &&
      // bounds do not conflict with each other
      Number(updatedParams[minName]) >= Number(updatedParams[maxName])
    ) {
      const errorLabel =
        minName[0].toUpperCase() +
        minName
          .slice(1)
          .split(/(?=[A-Z])/)
          .join(" ");

      updatedParamErrors[maxName] = `*Must be greater than ${errorLabel}`;
    }

    return updatedParamErrors;
  };

  return (
    <Container>
      <AdditionalParamLabelContainer
        style={checkedParams ? { background: "white" } : { background: "var(--light-gray)" }}
      >
        <CheckboxWidget
          color={"secondary"}
          size={"small"}
          handleCheckbox={(bool) => setCheckedParams(bool)}
          checkedState={checkedParams}
        />
        <AdditionalParamLabel>Use Additional Analysis Parameters</AdditionalParamLabel>
        {checkedParams && (
          <PresetDropdownContainer>
            <div style={{ marginRight: "10px" }}>Select Preset:</div>
            <DropDownWidget
              options={userPresets.map(({ name }) => name)}
              reset={!checkedParams}
              disabled={userPresets.length === 0} // disable if no presets have been saved
              handleSelection={(idx) => setSelectedPresetIdx(idx)}
              boxShadow="none"
            />
          </PresetDropdownContainer>
        )}
      </AdditionalParamLabelContainer>
      {!checkedParams && <WAOverlay />}
      <InputContainerOne style={{ paddingTop: "2%" }}>
        <AnalysisParamContainer
          label="Save Parameters as Preset"
          name="saveAnalysisPreset"
          tooltipText="When selected, the parameters will be saved and available for use in preset dropdown."
        >
          <InputErrorContainer>
            <CheckboxWidget
              checkedState={savePresetChecked}
              handleCheckbox={(bool) => {
                setSavePresetChecked(bool);
                // want to reset this in case there was an error and doesn't block submitting analysis
                if (!bool) validatePresetName("");
                // when initially checked and input is blank, need to ensure it's required
                else setParamErrors({ ...paramErrors, presetName: "*Required" });
              }}
            />
          </InputErrorContainer>
        </AnalysisParamContainer>
        {savePresetChecked && (
          <AnalysisParamContainer
            label="Enter Preset Name"
            name="presetName"
            tooltipText="Specifies name of analysis preset shown in dropdown options."
            value={analysisPresetName}
            changeFn={(e) => {
              validatePresetName(e.target.value);
            }}
            errorMsg={errorMessages.presetName}
          />
        )}
        <LineSeparator />
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
              initialSelected={getDropdownInitialSelection(
                "selectedPulse3dVersion",
                pulse3dFilteredFileVersions
              )}
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
              whiteSpace: "normal",
            }}
            iconStyle={{ fontSize: 20, margin: "10px 10px", right: "33px", position: "relative" }}
          >
            <DropDownContainer>
              <DropDownWidget
                options={Object.keys(stimWaveformFormatDetails)}
                reset={!checkedParams}
                initialSelected={getDropdownInitialSelection(
                  "stimWaveformFormat",
                  Object.values(stimWaveformFormatDetails)
                )}
                handleSelection={(idx) => {
                  updateParams({
                    stimWaveformFormat: Object.values(stimWaveformFormatDetails)[idx],
                  });
                }}
              />
            </DropDownContainer>
          </AnalysisParamContainer>
        )}

        <AnalysisParamContainer
          label="Show Stimulation Protocols"
          name="showStimSheet"
          tooltipText="When selected, adds a sheet to output file with stimulation protocols."
        >
          <InputErrorContainer>
            <CheckboxWidget
              checkedState={checkedParams ? disableStimProtocols : false}
              handleCheckbox={() => {
                updateParams({
                  showStimSheet: !disableStimProtocols,
                });
              }}
            />
          </InputErrorContainer>
        </AnalysisParamContainer>
        {pulse3dVersionGte("1.0.0") && (
          // TODO only show this for nautilai analyses
          <AnalysisParamContainer
            label="Normalization Method"
            name="normalizationMethod"
            tooltipText="Select the normalization method of data (Nautilai only)"
          >
            <DropDownContainer>
              <DropDownWidget
                options={nautilaiNormalizationMethods}
                reset={!checkedParams}
                initialSelected={getDropdownInitialSelection(
                  "normalizationMethod",
                  nautilaiNormalizationMethods
                )}
                handleSelection={(idx) => {
                  updateParams({
                    normalizationMethod: nautilaiNormalizationMethods[idx],
                  });
                }}
              />
            </DropDownContainer>
          </AnalysisParamContainer>
        )}
        {/* TODO only show this for MA analyses */}
        <AnalysisParamContainer
          label="Disable Y-Axis Normalization"
          name="normalizeYAxis"
          tooltipText="When selected, disables normalization of the y-axis."
        >
          <InputErrorContainer>
            <CheckboxWidget
              checkedState={checkedParams ? disableYAxisNormalization : false}
              handleCheckbox={(disable) => {
                updateParams({
                  normalizeYAxis: !disable,
                });
              }}
            />
          </InputErrorContainer>
        </AnalysisParamContainer>
        {/* TODO only show this for MA analyses */}
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
            iconStyle={{ fontSize: 20, margin: "0px 10px" }}
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
                initialSelected={getDropdownInitialSelection(
                  "stiffnessFactor",
                  Object.values(stiffnessFactorDetails)
                )}
              />
            </DropDownContainer>
          </AnalysisParamContainer>
        )}
        {pulse3dVersionGte("0.34.2") && (
          <AnalysisParamContainer
            label="Data Type"
            name="dataType"
            tooltipText="Specifies the type of data in the recording. If set to 'auto', will use the value encoded in the recording metadata."
            additionaLabelStyle={{ width: "62%", lineHeight: 2.5 }}
            iconStyle={{ fontSize: 20, margin: "0px 10px" }}
          >
            <DropDownContainer>
              <DropDownWidget
                options={Object.keys(dataTypeDetails)}
                reset={!checkedParams}
                handleSelection={(idx) => {
                  updateParams({
                    dataType: Object.values(dataTypeDetails)[idx],
                  });
                }}
                initialSelected={getDropdownInitialSelection("dataType", Object.values(dataTypeDetails))}
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
            additionalLabelStyle={{
              width: "102%",
              whiteSpace: "normal",
            }}
            iconStyle={{ fontSize: 20, margin: "10px 10px", right: "70px", position: "relative" }}
            changeFn={(e) => {
              updateParams({
                wellsWithFlippedWaveforms: e.target.value,
              });
            }}
            errorMsg={errorMessages.wellsWithFlippedWaveforms}
          />
        )}
        {pulse3dVersionGte("0.30.3") && (
          <WellGroups
            setAnalysisParams={setAnalysisParams}
            analysisParams={analysisParams}
            setWellGroupErr={setWellGroupErr}
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
        <SectionLabel>Windowed Analysis</SectionLabel>
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
        {useNoiseBasedPeakFinding() ? (
          <NoiseBasedAdvAnalysisContainer>
            <NoiseBasedPeakFindingAdvAnalysisParams
              analysisParams={analysisParams}
              checkedParams={checkedParams}
              updateParams={updateParams}
              errorMessages={errorMessages}
            />
          </NoiseBasedAdvAnalysisContainer>
        ) : (
          <OriginalAdvAnalysisContainer>
            <OrginalPeakFindingAdvAnalysisParams
              analysisParams={analysisParams}
              checkedParams={checkedParams}
              updateParams={updateParams}
              errorMessages={errorMessages}
            />
          </OriginalAdvAnalysisContainer>
        )}
      </InputContainerTwo>
      <ModalWidget
        open={deprecationNotice}
        labels={[pulse3dVersionEOLDateWarning]}
        closeModal={() => {
          setDeprecationNotice(false);
        }}
        header={"Attention!"}
      />
    </Container>
  );
}
