import styled from "styled-components";
import { useEffect, useState, useContext, useMemo } from "react";
import DropDownWidget from "../basicWidgets/DropDownWidget";
import WaveformGraph from "./WaveformGraph";
import { WellTitle as LabwareDefinition } from "@/utils/labwareCalculations";
import CircularSpinner from "../basicWidgets/CircularSpinner";
import ButtonWidget from "../basicWidgets/ButtonWidget";
import ModalWidget from "../basicWidgets/ModalWidget";
import { UploadsContext } from "@/components/layouts/DashboardLayout";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";
import semverGte from "semver/functions/gte";
import FormInput from "@/components/basicWidgets/FormInput";
import { AuthContext } from "@/pages/_app";
import CheckboxWidget from "@/components/basicWidgets/CheckboxWidget";

const twentyFourPlateDefinition = new LabwareDefinition(4, 6);

const Container = styled.div`
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const HeaderContainer = styled.div`
  font-size: 24px;
  margin: 20px;
  cursor: default;
`;

const WellDropdownContainer = styled.div`
  height: 30px;
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 200px;
`;

const WellDropdownLabel = styled.span`
  line-height: 2;
  font-size: 20px;
  white-space: nowrap;
  padding-right: 15px;
  cursor: default;
`;

const ParamContainer = styled.div`
  height: 60px;
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 650px;
  justify-content: left;
`;

const ParamLabel = styled.span`
  line-height: 2;
  font-size: 16px;
  width: 30%;
  margin-right: 19px;
  position: relative;
  white-space: nowrap;
  width: 47%;
  margin-right: 19px;
  position: relative;
  display: flex;
  align-items: center;
  cursor: default;
  justify-content: left;
`;

const GraphContainer = styled.div`
  border-radius: 7px;
  background-color: var(--med-gray);
  position: relative;
  width: 1350px;
  margin-top: 2%;
  overflow: hidden;
  padding: 0px 15px;
  display: flex;
  flex-direction: column;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const SpinnerContainer = styled.div`
  height: 448px;
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: center;
`;
const ButtonContainer = styled.div`
  position: relative;
  height: 50px;
  width: 100%;
  margin-bottom: 25px;
  display: flex;
  justify-content: flex-end;
  margin-bottom: 25px;
`;

const OuterParamContainer = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: left;
  padding-left: 13%;
  margin: 37px 0;
`;

const TooltipText = styled.span`
  font-size: 15px;
`;

const IconStyle = {
  marginLeft: "5px",
  "&:hover": {
    color: "var(--teal-green)",
    cursor: "pointer",
  },
};

const constantModalLabels = {
  success: {
    header: "Success!",
    messages: [
      "You have successfully started a new analysis.",
      "It will appear in the uploads table shortly.",
    ],
    buttons: ["Close"],
  },
  error: {
    header: "Error Occurred!",
    messages: ["There was an issue while attempting to start this analysis.", "Please try again later."],
    buttons: ["Close"],
  },
  duplicate: {
    header: "Warning!",
    messages: ["Consecutive peaks and/or valleys were detected in the following wells:"],
    buttons: ["Back", "Run Analysis"],
  },
  oldPulse3dVersion: {
    header: "Warning!",
    messages: [
      "Interactive analysis is using a newer version of Pulse3D than the version originally used on this recording. Peaks and valleys may be slightly different.",
      "Please re-analyze this recording using a Pulse3D version greater than 0.28.3 or continue.",
    ],
    buttons: ["Close"],
  },
  dataFound: {
    header: "Important!",
    messages: ["Previous changes have been found for this analysis.", "Do you want to use it or start over?"],
    buttons: ["Start Over", "Use"],
  },
  removeDuplicates: {
    header: "Important!",
    messages: [
      "This action will be performed on all wells and can only be undone if no other changes have been made.",
      "Please confirm to continue.",
    ],
    buttons: ["Cancel", "Continue"],
  },
};

const wellNames = Array(24)
  .fill()
  .map((_, idx) => twentyFourPlateDefinition.getWellNameFromIndex(idx));

const ACTIONS = {
  ADD: "add",
  UNDO: "undo",
  RESET: "reset",
};

const getDefaultCustomAnalysisSettings = () => {
  const customVals = {
    // add values that apply to all wells
    windowedAnalysisBounds: {
      start: null,
      end: null,
    },
  };
  // add per well values
  for (const well of wellNames) {
    customVals[well] = {
      allFeatureIndices: {
        peaks: [],
        valleys: [],
      },
      filteredFeatureIndices: {
        peaks: [],
        valleys: [],
      },
      duplicateFeatureIndices: {
        peaks: [],
        valleys: [],
      },
      thresholdEndpoints: {
        peaks: {
          y1: null,
          y2: null,
        },
        valleys: {
          y1: null,
          y2: null,
        },
      },
    };
  }
  return customVals;
};

const getDefaultChangelog = () => {
  const changelog = {};
  for (const well of wellNames) {
    changelog[well] = [];
  }
  return changelog;
};

const title = (s) => {
  return s.charAt(0).toUpperCase() + s.slice(1);
};

export default function InteractiveWaveformModal({
  selectedJob,
  setOpenInteractiveAnalysis,
  numberOfJobsInUpload,
}) {
  const { usageQuota } = useContext(AuthContext);
  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);

  const [creditUsageAlert, setCreditUsageAlert] = useState(false);
  const [pulse3dVersionIdx, setPulse3dVersionIdx] = useState(0);
  const [filteredVersions, setFilteredVersions] = useState([]);
  const [deprecationNotice, setDeprecationNotice] = useState(false);
  const [pulse3dVersionEOLDate, setPulse3dVersionEOLDate] = useState("");
  const [nameOverride, setNameOverride] = useState();
  const [uploadInProgress, setUploadInProgress] = useState(false); // determines state of interactive analysis upload
  const [isLoading, setIsLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalLabels, setModalLabels] = useState(constantModalLabels.success);

  const [removeDupsChecked, setRemoveDupsChecked] = useState(false);
  const [removeDupsWarning, setRemoveDupsWarning] = useState(false);
  const [disableRemoveDupsCheckbox, setDisableRemoveDupsCheckbox] = useState(false);

  const [selectedWell, setSelectedWell] = useState("A1");
  const wellIdx = twentyFourPlateDefinition.getWellIndexFromName(selectedWell);

  const [originalAnalysisData, setOriginalAnalysisData] = useState({}); // original waveforms and peaks/valleys for each well from GET request, unedited
  const wellWaveformData =
    originalAnalysisData.coordinates && originalAnalysisData.coordinates[selectedWell]
      ? originalAnalysisData.coordinates[selectedWell]
      : [];
  const [baseData, setBaseData] = useState({}); // same originalAnalysisData.featuresForWells but can have dups removed
  const [timepointRange, setTimepointRange] = useState({
    // This is a copy of the max/min timepoints of the data. Windowed analysis start/stop times are set in customAnalysisSettings.windowedAnalysisBounds
    // Must be stored in its own state and not tied directly to the recording data because it will be set to the start/stop times of the job if
    // They were set
    min: null,
    max: null,
  });

  const [customAnalysisSettings, setCustomAnalysisSettings] = useState(getDefaultCustomAnalysisSettings());
  // This only exists as a convenience for passing data down to WaveformGraph. It's a copy of customAnalysisSettings with only the data relevant for the selected well
  const [customAnalysisSettingsForWell, setCustomAnalysisSettingsForWell] = useState({});
  const [customAnalysisSettingsChanges, setCustomAnalysisSettingsChanges] = useState([]);
  const [changelog, setChangelog] = useState(getDefaultChangelog());
  const [openChangelog, setOpenChangelog] = useState(false);
  const [prevAction, setPrevAction] = useState();

  const appendToChangelog = (msg) => {
    const changelogCopy = JSON.parse(JSON.stringify(changelog));
    changelogCopy[selectedWell].push(msg);
    setChangelog(changelogCopy);
  };

  const updateCustomAnalysisSettings = (newCustomAnalysisSettings) => {
    newCustomAnalysisSettings = JSON.parse(JSON.stringify(newCustomAnalysisSettings));
    for (const well of wellNames) {
      newCustomAnalysisSettings[well].filteredFeatureIndices = filterAndSortFeatures(
        originalAnalysisData.coordinates[well],
        newCustomAnalysisSettings.windowedAnalysisBounds,
        newCustomAnalysisSettings[well]
      );
      newCustomAnalysisSettings[well].duplicateFeatureIndices = checkDuplicates(
        newCustomAnalysisSettings[well].filteredFeatureIndices
      );
    }
    setCustomAnalysisSettings(newCustomAnalysisSettings);
  };

  // TODO does anything need to happen after these?
  const customAnalysisSettingsInitializers = {
    windowBounds: (initialBounds) => {
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        windowedAnalysisBounds: JSON.parse(JSON.stringify(initialBounds)),
      });
    },
    featureIndices: (well, featureName, initialIndices) => {
      const wellSettings = customAnalysisSettings[well];
      wellSettings.allFeatureIndices[featureName] = JSON.parse(JSON.stringify(initialIndices));
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        [well]: wellSettings,
      });
    },
    thresholdEndpoints: (well, featureName, initialValue) => {
      const wellSettings = customAnalysisSettings[well];
      wellSettings.thresholdEndpoints[featureName] = {
        y1: initialValue,
        y2: initialValue,
      };
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        [well]: wellSettings,
      });
    },
  };

  const customAnalysisSettingsUpdaters = {
    // These functions will always update the changelog
    setWindowBounds: (newBounds) => {
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        windowedAnalysisBounds: {
          ...customAnalysisSettings.customAnalysisSettings,
          ...newBounds,
        },
      });
      // TODO this should NOT update the changelog, it should just apply to the current state.
      // Also need to make sure that if undo is pressed that the window bounds are reapplied to the prev state,
      // will prob have to just rerun filtering to do this
    },
    addFeature: (featureName, timepoint) => {
      const wellSettings = customAnalysisSettings[selectedWell];
      const wellFeatureIndices = wellSettings.allFeatureIndices[featureName];
      const idxToAdd = wellWaveformData.findIndex(
        (coord) => Number(coord[0].toFixed(2)) === Number(timepoint.toFixed(2))
      );

      wellFeatureIndices.push(idxToAdd);
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        [selectedWell]: wellSettings,
      });

      // TODO: Should probably make a function for the next two lines
      const [x, y] = wellWaveformData[idxToAdd];
      const changelogMsg = `${title(featureName)} at [ ${x.toFixed(2)}, ${y.toFixed(2)} ] was added.`;
      appendToChangelog(changelogMsg);
    },
    deleteFeature: (featureName, idxToDelete) => {
      const wellSettings = customAnalysisSettings[selectedWell];
      const wellFeatureIndices = wellSettings.allFeatureIndices[featureName];

      const targetIdx = wellFeatureIndices.indexOf(idxToDelete);
      if (targetIdx === -1) return;

      wellFeatureIndices.splice(targetIdx, 1);
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        [selectedWell]: wellSettings,
      });

      const [x, y] = wellWaveformData[targetIdx];
      const changelogMsg = `${title(featureName)} at [ ${x.toFixed(2)}, ${y.toFixed(2)} ] was removed.`;
      appendToChangelog(changelogMsg);
    },
    moveFeature: (featureName, originalIdx, newIdx) => {
      const wellSettings = customAnalysisSettings[selectedWell];
      const wellFeatureIndices = wellSettings.allFeatureIndices[featureName];

      const targetIdx = wellFeatureIndices.indexOf(originalIdx);
      if (targetIdx === -1) return;

      wellFeatureIndices.splice(targetIdx, 1, newIdx);
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        [selectedWell]: wellSettings,
      });

      // TODO make sure this works
      const [oldX, oldY] = wellWaveformData[originalIdx];
      const [newX, newY] = wellWaveformData[newIdx];
      const changelogMsg = `${title(featureName)} at [ ${oldX.toFixed(2)}, ${oldY.toFixed(
        2
      )} ] was moved to [ ${newX.toFixed(2)}, ${newY.toFixed(2)} ].`;
      appendToChangelog(changelogMsg);
    },
    setThresholdEndpoint: (featureName, endpointName, newValue) => {
      const wellSettings = customAnalysisSettings[selectedWell];

      wellSettings.thresholdEndpoints[featureName][endpointName] = newValue;
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        [selectedWell]: wellSettings,
      });

      const changelogMsg = `${title(featureName)} Line ${title(endpointName)} switched to ${newValue}`;
      appendToChangelog(changelogMsg);
    },
  };

  // TODO explain this
  useEffect(() => {
    const compatibleVersions = pulse3dVersions.filter((v) => semverGte(v, "0.28.3"));
    setFilteredVersions([...compatibleVersions]);

    if (usageQuota && usageQuota.limits && numberOfJobsInUpload >= 2 && usageQuota.limits.jobs !== -1) {
      setCreditUsageAlert(true);
    }
  }, []);

  // TODO explain this
  useEffect(() => {
    if (removeDupsChecked) {
      const baseDataCopy = JSON.parse(JSON.stringify(baseData));
      for (const well in baseDataCopy) {
        const { duplicateFeatureIndices } = customAnalysisSettings[well];
        // console.log("!!!", well, duplicateFeatureIndices);
        baseDataCopy[well][0] = removeDups(baseDataCopy[well][0], duplicateFeatureIndices.peaks);
        baseDataCopy[well][1] = removeDups(baseDataCopy[well][1], duplicateFeatureIndices.valleys);
      }
      setBaseData(baseDataCopy);
    } else if (originalAnalysisData.featuresForWells) {
      // if unchecked, revert back to previous peaks and valleys
      setBaseData(originalAnalysisData.featuresForWells);
    }
  }, [removeDupsChecked]);

  // TODO explain this
  useEffect(() => {
    for (const well of wellNames) {
      if (baseData[well]) {
        // This is just to update the custom peaks and valleys correctly after the useEffect above, or after baseData is initially set
        customAnalysisSettingsInitializers.featureIndices(well, "peaks", baseData[well][0]);
        customAnalysisSettingsInitializers.featureIndices(well, "valleys", baseData[well][1]);
      }
    }
  }, [baseData]);

  // TODO explain this
  useEffect(() => {
    if (wellWaveformData.length > 0) {
      setIsLoading(false);
    }
  }, [wellWaveformData]);

  // set peak and valley markers if not already set and the data required to set them is present
  useEffect(() => {
    const { peaks, valleys } = customAnalysisSettings[selectedWell].thresholdEndpoints;
    if (
      [peaks.y1, peaks.y2, valleys.y1, valleys.y1].filter((val) => val == null).length > 0 &&
      originalAnalysisData.featuresForWells &&
      originalAnalysisData.featuresForWells[selectedWell]
    ) {
      setBothLinesToDefault();
    }
  }, [selectedWell, wellWaveformData]);

  // update customAnalysisSettingsForWell whenever customAnalysisSettings or the currently selected well changes
  useEffect(() => {
    // console.log("$$$ filtered", customAnalysisSettings[selectedWell].filteredFeatureIndices);
    // console.log("$$$ dups", customAnalysisSettings[selectedWell].duplicateFeatureIndices);
    setCustomAnalysisSettingsForWell(
      // Tanner (6/1/23): Copying just to be safe
      JSON.parse(
        JSON.stringify({
          windowedAnalysisBounds: customAnalysisSettings.windowedAnalysisBounds,
          featureIndices: customAnalysisSettings[selectedWell].filteredFeatureIndices,
          duplicateIndices: customAnalysisSettings[selectedWell].duplicateFeatureIndices,
          thresholdEndpoints: customAnalysisSettings[selectedWell].thresholdEndpoints,
        })
      )
    );
  }, [customAnalysisSettings, selectedWell]);

  // TODO
  // update the change tracker whenever prev action is set, which should always and only occur immediately after the changelog is updated
  useEffect(() => {
    const customAnalysisSettingsChangesCopy = JSON.parse(JSON.stringify(customAnalysisSettingsChanges));
    const customAnalysisSettingsCopy = JSON.parse(JSON.stringify(customAnalysisSettings));

    if (prevAction === ACTIONS.ADD) {
      customAnalysisSettingsChangesCopy.push(customAnalysisSettingsCopy);
    } else if (prevAction === ACTIONS.UNDO) {
      // TODO there is probably more handling that needs to be done here
      customAnalysisSettingsChangesCopy.splice(customAnalysisSettingsChangesCopy.length - 1, 1);
    } else if (prevAction === ACTIONS.RESET) {
      customAnalysisSettingsChangesCopy.splice(0, customAnalysisSettingsChangesCopy.length);
    }
    setCustomAnalysisSettingsChanges(customAnalysisSettingsChangesCopy);
  }, [prevAction]);

  const getNewData = async () => {
    await getWaveformData(true, "A1");
  };

  const getWaveformData = async (featuresNeeded, well) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/waveform-data?upload_id=${selectedJob.uploadId}&job_id=${selectedJob.jobId}&peaks_valleys=${featuresNeeded}&well_name=${well}`
      );
      if (response.status !== 200) throw Error();

      const res = await response.json();
      if (res.error) throw Error();

      if (!("coordinates" in originalAnalysisData)) {
        originalAnalysisData = {
          featuresForWells: res.peaks_valleys,
          coordinates: {},
        };
        setBaseData(res.peaks_valleys);
      }

      const { coordinates } = res;
      // original data is set and never changed to hold original state in case of reset
      originalAnalysisData.coordinates[well] = coordinates;
      setOriginalAnalysisData(originalAnalysisData);

      if (featuresNeeded) {
        const { start_time, end_time } = selectedJob.analysisParams;
        const newTimepointRange = {
          min: start_time || Math.min(...coordinates.map((coords) => coords[0])),
          max: end_time || Math.max(...coordinates.map((coords) => coords[0])),
        };
        setTimepointRange(newTimepointRange);
        resetWindowBounds(newTimepointRange);

        // won't be present for older recordings or if no replacement was ever given
        if ("nameOverride" in selectedJob) setNameOverride(selectedJob.nameOverride);
      }

      if (!semverGte(selectedJob.analysisParams.pulse3d_version, "0.28.3")) {
        setModalLabels(constantModalLabels.oldPulse3dVersion);
        setModalOpen("pulse3dWarning");
      }
    } catch (e) {
      console.log("ERROR getting waveform data: ", e);
      // open error modal and kick users back to /uploads page if random  error
      setModalLabels(constantModalLabels.error);
      setModalOpen("status");
    }
  };

  const findInitialThresholdForFeature = (well, featureType) => {
    const { coordinates, featuresForWells } = originalAnalysisData;
    const { max, min } = timepointRange;

    const compare = (a, b) => {
      return featureType === "peaks" ? a < b : a > b;
    };

    const featureIdx = featureType === "peaks" ? 0 : 1;

    const wellSpecificFeatures = featuresForWells[well][featureIdx];
    const wellSpecificCoords = coordinates[well];

    // consider when no features were found in a well
    if (wellSpecificCoords && wellSpecificFeatures.length > 0) {
      // arbitrarily set to first feature
      let idxOfThresholdValue = wellSpecificFeatures[0];

      wellSpecificFeatures.map((featureIdx) => {
        const [testX, testY] = wellSpecificCoords[featureIdx];
        const currentTresholdY = wellSpecificCoords[idxOfThresholdValue][1];
        // only use features inside windowed analysis times
        const isLessThanEndTime = !max || testX <= max;
        const isGreaterThanStartTime = !min || testX >= min;
        // filter for features inside windowed time
        if (compare(testY, currentTresholdY) && isGreaterThanStartTime && isLessThanEndTime) {
          idxOfThresholdValue = featureIdx;
        }
      });

      // return y coordinate of idx
      return wellSpecificCoords[idxOfThresholdValue][1];
    }
  };

  const resetWindowBounds = (bounds = timepointRange) => {
    customAnalysisSettingsInitializers.windowBounds({
      start: bounds.min,
      end: bounds.max,
    });
  };

  const loadExistingData = () => {
    // this happens very fast so not storing to react state the first call, see line 162 (? different line now)
    const jsonData = sessionStorage.getItem(selectedJob.jobId);
    const existingData = JSON.parse(jsonData);
    // TODO test this, also should probably use initializers here
    setCustomAnalysisSettings(existingData);
  };

  const handleWellSelection = async (idx) => {
    const wellName = wellNames[idx];
    if (wellName !== selectedWell) {
      setSelectedWell(wellName);
      if (!(wellName in originalAnalysisData.coordinates)) {
        setIsLoading(true);
        getWaveformData(false, wellName);
      }
    }
  };

  const resetWellChanges = () => {
    // reset peaks and valleys for current well
    const changelogCopy = JSON.parse(JSON.stringify(changelog));
    changelogCopy[selectedWell] = [];
    setChangelog(changelogCopy);
    // reset state
    resetWindowBounds();
    customAnalysisSettingsInitializers.featureIndices(selectedWell, "peaks", baseData[selectedWell][0]);
    customAnalysisSettingsInitializers.featureIndices(selectedWell, "valleys", baseData[selectedWell][1]);
    setBothLinesToDefault();
    setDisableRemoveDupsCheckbox(isRemoveDuplicatesDisabled(changelogCopy));
  };

  const postNewJob = async () => {
    try {
      setUploadInProgress(true);

      // TODO check that this is formatted correctly
      const filteredFeatures = {};
      for (const well in customAnalysisSettings) {
        filteredFeatures[well] = customAnalysisSettings[well].filteredFeatureIndices;
      }

      const prevPulse3dVersion = selectedJob.analysisParams.pulse3d_version;
      const { start, end: endTime } = customAnalysisSettings.windowedAnalysisBounds;
      // jobs run on pulse3d versions < 0.28.3 will not have a 0 timepoint so account for that here that 0.01 is still the first time point, not windowed
      const startTime = !semverGte(prevPulse3dVersion, "0.28.3") && start == 0.01 ? null : end;

      // reassign new peaks and valleys if different
      const requestBody = {
        ...selectedJob.analysisParams,
        upload_id: selectedJob.uploadId,
        peaks_valleys: filteredFeatures,
        start_time: startTime,
        end_time: endTime,
        version: filteredVersions[pulse3dVersionIdx],
        previous_version: prevPulse3dVersion,
      };

      // only add for versions greater than 0.32.2
      if (semverGte(prevPulse3dVersion, "0.32.2"))
        requestBody.name_override = nameOverride === "" ? null : nameOverride;

      const jobResponse = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs`, {
        method: "POST",
        body: JSON.stringify(requestBody),
      });

      if (jobResponse.status !== 200) {
        // TODO make modal
        console.log("ERROR posting new job: ", await jobResponse.json());
        setModalLabels(constantModalLabels.error);
      } else {
        setModalLabels(constantModalLabels.success);
      }

      setUploadInProgress(false);
      setModalOpen("status");
      // once interactive analysis is closed, clear storage.
      // currently clearing for successful uploads
      sessionStorage.removeItem(selectedJob.jobId);
    } catch (e) {
      console.log("ERROR posting new job", e);
      setModalLabels(constantModalLabels.error);
      setUploadInProgress(false);
      setModalOpen("status");
    }
  };

  const handleModalClose = (i) => {
    if (modalOpen !== "pulse3dWarning") {
      if (modalOpen === "status") setOpenInteractiveAnalysis(false);
      else if (i === 0) {
        getNewData();
      } else {
        loadExistingData();
      }
      sessionStorage.removeItem(selectedJob.jobId);
    }

    setModalOpen(false);
  };

  const saveChanges = () => {
    // TODO TANNER make sure this works
    // TODO handle if for some reason this is full and returns error
    sessionStorage.setItem(selectedJob.jobId, JSON.stringify(customAnalysisSettings));
  };

  //     changelogMessage = `Peak at [ ${oldPeakX.toFixed(2)}, ${oldPeakY.toFixed(
  //       2
  //     )} ] was moved to [ ${newPeakX.toFixed(2)}, ${newPeakY.toFixed(2)} ].`;
  //   } else if (peakAdded) {
  //     const newIdx = compareFeatures(peaksToCompare, featuresForWell[0]);
  //     if (newIdx >= 0) {
  //       const coordinates = dataToGraph[newIdx];
  //       changelogMessage = `Peak was added at [ ${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(2)} ]`;
  //     }
  //   } else if (peakDeleted) {
  //     const newIdx = compareFeatures(featuresForWell[0], peaksToCompare);
  //     if (newIdx >= 0) {
  //       const coordinates = dataToGraph[newIdx];
  //       changelogMessage = `Peak at [ ${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(
  //         2
  //       )} ] was removed.`;
  //     }
  //   } else if (valleysMoved) {
  //     const diffIdx = valleysToCompare.findIndex((valleyIdx, i) => valleyIdx !== featuresForWell[1][i]),
  //       oldValleyX = wellWaveformData[valleysToCompare[diffIdx]][0],
  //       oldValleyY = wellWaveformData[valleysToCompare[diffIdx]][1],
  //       newValleyX = wellWaveformData[featuresForWell[1][diffIdx]][0],
  //       newValleyY = wellWaveformData[featuresForWell[1][diffIdx]][1];

  //     changelogMessage = `Valley at [ ${oldValleyX.toFixed(2)}, ${oldValleyY.toFixed(
  //       2
  //     )} ] was moved to [ ${newValleyX.toFixed(2)}, ${newValleyY.toFixed(2)} ].`;
  //   } else if (valleyAdded) {
  //     const newIdx = compareFeatures(valleysToCompare, featuresForWell[1]);
  //     if (newIdx >= 0) {
  //       const coordinates = dataToGraph[newIdx];
  //       changelogMessage = `Valley was added at [ ${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(
  //         2
  //       )} ]`;
  //     }
  //   } else if (valleyDeleted) {
  //     const newIdx = compareFeatures(featuresForWell[1], valleysToCompare);
  //     if (newIdx >= 0) {
  //       const coordinates = dataToGraph[newIdx];
  //       changelogMessage = `Valley at [ ${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(
  //         2
  //       )} ] was removed.`;
  //     }
  //   } else if (windowedTimeDiff) {
  //     changelogMessage = `Start time was changed from ${startToCompare} to ${editableStartEndTimes.startTime} and end time was changed from ${endToCompare} to ${editableStartEndTimes.endTime}.`;
  //   } else if (startTimeDiff) {
  //     changelogMessage = `Start time was changed from ${startToCompare} to ${editableStartEndTimes.startTime}.`;
  //   } else if (endTimeDiff) {
  //     changelogMessage = `End time was changed from ${endToCompare} to ${editableStartEndTimes.endTime}.`;
  //   } else if (isNewValleyY1 && isNewValleyY2) {
  //     changelogMessage = `Valley Line moved ${valleyY1[wellIdx] - valleyY1ToCompare}`;
  //   } else if (isNewPeakY1 && isNewPeakY2) {
  //     changelogMessage = `Peak Line moved ${peakY1[wellIdx] - peakY1ToCompare}`;
  //   } else if (isNewValleyY1) {
  //     changelogMessage = `Valley Line Y1 switched to ${valleyY1[wellIdx]}`;
  //   } else if (isNewValleyY2) {
  //     changelogMessage = `Valley Line Y2 switched to ${valleyY2[wellIdx]}`;
  //   } else if (isNewPeakY1) {
  //     changelogMessage = `Peak Line Y1 switched to ${peakY1[wellIdx]}`;
  //   } else if (isNewPeakY2) {
  //     changelogMessage = `Peak Line Y2 switched to ${peakY2[wellIdx]}`;
  //   }

  //   return changelogMessage;
  // };

  const handleVersionSelect = (idx) => {
    const selectedVersionMetadata = metaPulse3dVersions.filter(
      (version) => version.version === pulse3dVersions[idx]
    )[0];

    // TODO figure out why there is an extra space here
    setPulse3dVersionEOLDate(
      selectedVersionMetadata.end_of_life_date
        ? ` Version ${selectedVersionMetadata.version} will be removed after ${selectedVersionMetadata.end_of_life_date}.`
        : `Version ${selectedVersionMetadata.version} will be removed soon.`
    );
    setDeprecationNotice(selectedVersionMetadata.state === "deprecated");
    setPulse3dVersionIdx(idx);
  };

  const handleRunAnalysis = () => {
    const wellsWithDups = [];
    // TODO make sure this is working correctly
    Object.keys(customAnalysisSettings).map((well) => {
      const { duplicatePeaks, duplicateValleys } = customAnalysisSettings[well];
      if (duplicatePeaks.length > 0 || duplicateValleys.length > 0) wellsWithDups.push(well);
    });

    if (wellsWithDups.length > 0) {
      const wellsWithDupsString = wellsWithDups.join(", ");
      constantModalLabels.duplicate.messages.splice(1, 1, wellsWithDupsString);
      setModalOpen("duplicatesFound");
    } else {
      postNewJob();
    }
  };

  const undoLastChange = () => {
    // if (changelog[selectedWell] && changelog[selectedWell].length > 0) {
    //   // undoing state tells the updateChangelog useEffect to not ignore the change and not as a new change
    //   setUndoing(true);
    //   // make copies so you control when state is updated
    //   const changesCopy = JSON.parse(JSON.stringify(changelog[selectedWell]));
    //   // const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
    //   const newWindowTimes = {};
    //   // remove step with latest changes
    //   changesCopy.pop();
    //   if (changesCopy.length > 0) {
    //     // grab state from the step before the undo step to set as current state
    //     const { peaks, valleys, startTime, endTime, valleyYOne, valleyYTwo, peakYOne, peakYTwo } =
    //       changesCopy[changesCopy.length - 1];
    //     // set old peaks and valleys to well
    //     // peaksValleysCopy[selectedWell] = [[...peaks], [...valleys]];
    //     newWindowTimes.startTime = startTime;
    //     newWindowTimes.endTime = endTime;
    //     // TODO use new updater for this
    //     // setBothLinesToNew(peakYOne, peakYTwo, valleyYOne, valleyYTwo);
    //   } else {
    //     // if undoing the very first change, revert back to original state
    //     newWindowTimes.startTime = timepointRange.min;
    //     newWindowTimes.endTime = timepointRange.max;
    //     // TODO handle features threshold endpoints
    //     // peaksValleysCopy[selectedWell] = originalAnalysisData.featuresForWells[selectedWell];
    //     setBothLinesToDefault();
    //   }
    //   // needs to be reassigned to hold state
    //   changelog[selectedWell] = changesCopy;
    //   // update values to state to rerender graph
    //   // setEditableStartEndTimes(newWindowTimes);
    //   // setEditablePeaksValleys(peaksValleysCopy);
    //   setDisableRemoveDupsCheckbox(isRemoveDuplicatesDisabled(changelog));
    //   setChangelog(changelog);
    // }
  };

  const pulse3dVersionGte = (version) => {
    return filteredVersions.length > 0 && semverGte(filteredVersions[pulse3dVersionIdx], version);
  };

  const handleDuplicatesModalClose = (isRunAnalysisOption) => {
    setModalOpen(false);
    if (isRunAnalysisOption) {
      postNewJob();
    }
  };

  const calculateYLimit = (y1, y2, markerX) => {
    const { start, end } = customAnalysisSettings.windowedAnalysisBounds;
    const slope = (y2 - y1) / (end - start);
    return y1 + slope * (markerX - start);
  };

  const setBothLinesToDefault = () => {
    customAnalysisSettingsInitializers.thresholdEndpoints(
      selectedWell,
      "peaks",
      findInitialThresholdForFeature(selectedWell, "peaks")
    );
    customAnalysisSettingsInitializers.thresholdEndpoints(
      selectedWell,
      "valleys",
      findInitialThresholdForFeature(selectedWell, "valleys")
    );
  };

  const filterAndSortFeatures = (
    wellCoords,
    windowedAnalysisBounds,
    { allFeatureIndices, thresholdEndpoints }
  ) => {
    allFeatureIndices = JSON.parse(JSON.stringify(allFeatureIndices));

    const { start, end } = windowedAnalysisBounds;

    let filteredAndSortedFeatures = {};
    for (const featureType in allFeatureIndices) {
      filteredAndSortedFeatures[featureType] = allFeatureIndices[featureType]
        .filter((idx) => {
          // Can only filter if the data for this well has actually been loaded,
          // which is not guaranteed to be the case with the staggered loading of data for each well
          if (!wellCoords) return true;

          const [featureMarkerX, featureMarkerY] = wellCoords[idx];
          const isFeatureWithinWindow = featureMarkerX >= start && featureMarkerX <= end;

          // TODO
          const featureThresholdY = calculateYLimit(
            thresholdEndpoints[featureType].y1,
            thresholdEndpoints[featureType].y2,
            featureMarkerX
          );
          const isFeatureWithinThreshold =
            featureType === "peaks"
              ? featureMarkerY >= featureThresholdY
              : featureMarkerY <= featureThresholdY;

          return isFeatureWithinThreshold && isFeatureWithinWindow;
        })
        .sort((a, b) => a - b);
    }
    return filteredAndSortedFeatures;
  };

  const checkDuplicates = (filteredFeatureIndices) => {
    const { peaks, valleys } = filteredFeatureIndices;

    // create list with all features in order
    const features = [];
    for (const idx of peaks) {
      features.push({ type: "peaks", idx });
    }
    for (const idx of valleys) {
      features.push({ type: "valleys", idx });
    }
    features.sort((a, b) => a.idx - b.idx);

    const duplicates = { peaks: [], valleys: [] };
    for (let i = 0; i < features.length; i++) {
      const [curr, next] = features.slice(i, i + 2);
      if (curr && next && curr.type === next.type) {
        duplicates[curr.type].push(curr.idx);
      }
    }

    return duplicates;
  };

  const removeDups = (allIndices, dupIndices) => {
    return allIndices.filter((idx) => !dupIndices.includes(idx));
  };

  const closeRemoveDuplicatesModal = async (idx) => {
    setRemoveDupsChecked(idx === 1);
    // close modal
    setModalOpen(false);
  };

  const handleCheckedDuplicateFeatures = (checked) => {
    // removeDupsWarning tracks if a user has seen this warning modal during the IA session.
    // we do not need to show it more than once per session
    if (checked) {
      if (removeDupsWarning) {
        // if user has seen the warning, immediately remove all duplicates
        closeRemoveDuplicatesModal(1);
      } else {
        // otherwise pop up modal letting user know the conditions of this action
        setRemoveDupsWarning(true);
        setModalOpen("removeDuplicates");
      }
    } else {
      setRemoveDupsChecked(false);
    }
  };

  const isRemoveDuplicatesDisabled = (changelogCopy) => {
    // 1. disable if remove duplicates has been checked and other changes have been made after or changes have been made first
    // 2. remove if other changes were made first before checking
    // 3. disable if in loading state
    return (
      // TODO check the change tracker here instead?
      (removeDupsChecked &&
        Object.keys(changelogCopy).some(
          (well) => changelogCopy[well].length > 0 && changelogCopy[well][0].removeDupsChecked
        )) ||
      Object.keys(changelog).some(
        (well) => changelogCopy[well].length > 0 && !changelog[well][0].removeDupsChecked
      ) ||
      isLoading
    );
  };

  // ENTRYPOINT
  // defined last so that everything required for it already exists
  // Luci (12-14-2022) this component gets mounted twice and we don't want this expensive function to request waveform data to be called twice. This ensures it is only called once per job selection
  useMemo(() => {
    const data = sessionStorage.getItem(selectedJob.jobId); // returns null if key doesn't exist in storage
    if (data) {
      // if data is found in sessionStorage then do ?
      setModalLabels(constantModalLabels.dataFound);
      setModalOpen("dataFound");
    } else {
      // if no data stored, then need to retrieve from server
      getNewData();
    }
  }, [selectedJob]);

  return (
    <Container>
      <HeaderContainer>Interactive Waveform Analysis</HeaderContainer>
      <WellDropdownContainer>
        <WellDropdownLabel>Select Well:</WellDropdownLabel>
        <DropDownWidget
          options={wellNames}
          handleSelection={handleWellSelection}
          disabled={isLoading}
          reset={selectedWell == "A1"}
          initialSelected={0}
        />
      </WellDropdownContainer>

      <GraphContainer>
        {isLoading ? (
          <SpinnerContainer>
            <CircularSpinner size={200} />
          </SpinnerContainer>
        ) : (
          <WaveformGraph
            timepointRange={timepointRange}
            waveformData={wellWaveformData}
            customAnalysisSettings={customAnalysisSettingsForWell}
            customAnalysisSettingsUpdaters={customAnalysisSettingsUpdaters}
            changelogActions={{
              save: saveChanges,
              undo: undoLastChange,
              reset: resetWellChanges,
              open: () => setOpenChangelog(true),
            }}
          />
        )}
      </GraphContainer>
      <OuterParamContainer>
        <ParamContainer>
          <ParamLabel htmlFor="removeDupFeatures">
            Remove Duplicate Peaks/Valleys:
            <Tooltip
              title={
                <TooltipText>
                  {
                    "Automatically remove duplicate peaks and valleys from all wells and can only be performed when no other changes have been made."
                  }
                </TooltipText>
              }
            >
              <InfoOutlinedIcon sx={IconStyle} />
            </Tooltip>
          </ParamLabel>
          <CheckboxWidget
            color={"secondary"}
            size={"small"}
            disabled={disableRemoveDupsCheckbox || isLoading}
            handleCheckbox={handleCheckedDuplicateFeatures}
            checkedState={removeDupsChecked}
          />
        </ParamContainer>
        <ParamContainer>
          <ParamLabel htmlFor="selectedPulse3dVersion">
            Pulse3d Version:
            <Tooltip
              title={
                <TooltipText>
                  {"Specifies which version of the pulse3d analysis software to use."}
                </TooltipText>
              }
            >
              <InfoOutlinedIcon sx={IconStyle} />
            </Tooltip>
          </ParamLabel>
          <div style={{ width: "140px" }}>
            <DropDownWidget
              options={pulse3dVersions.map((version) => {
                const selectedVersionMeta = metaPulse3dVersions.filter((meta) => meta.version === version);
                if (selectedVersionMeta[0] && selectedVersionMeta[0].state === "testing") {
                  return version + " " + "[ testing ]";
                } else if (selectedVersionMeta[0] && selectedVersionMeta[0].state === "deprecated") {
                  return version + " " + "[ deprecated ]";
                } else {
                  return version;
                }
              })}
              label="Select"
              reset={pulse3dVersionIdx === 0}
              handleSelection={handleVersionSelect}
              initialSelected={0}
            />
          </div>
        </ParamContainer>
        {pulse3dVersionGte("0.32.2") && (
          <ParamContainer>
            <ParamLabel htmlFor="nameOverride">
              Override Original Name:
              <Tooltip
                title={
                  <TooltipText>
                    {"This name will replace the original recording name for the ouput filename."}
                  </TooltipText>
                }
              >
                <InfoOutlinedIcon sx={IconStyle} />
              </Tooltip>
            </ParamLabel>
            <div style={{ width: "50%" }}>
              <FormInput
                name="nameOverride"
                placeholder={""}
                value={nameOverride}
                onChangeFn={(e) => {
                  setNameOverride(e.target.value);
                }}
              />
            </div>
          </ParamContainer>
        )}
      </OuterParamContainer>
      <ButtonContainer>
        <ButtonWidget
          width="200px"
          height="50px"
          position="relative"
          borderRadius="3px"
          left="-70px"
          label="Cancel"
          clickFn={() => setOpenInteractiveAnalysis(false)}
        />
        <ButtonWidget
          width="200px"
          height="50px"
          position="relative"
          borderRadius="3px"
          left="-50px"
          label="Run Analysis"
          backgroundColor={uploadInProgress || isLoading ? "var(--dark-gray)" : "var(--dark-blue)"}
          disabled={uploadInProgress || isLoading}
          inProgress={uploadInProgress}
          clickFn={handleRunAnalysis}
        />
      </ButtonContainer>
      <ModalWidget
        open={["status", "dataFound", "pulse3dWarning"].includes(modalOpen)}
        buttons={modalLabels.buttons}
        closeModal={handleModalClose}
        header={modalLabels.header}
        labels={modalLabels.messages}
      />
      <ModalWidget
        open={modalOpen === "duplicatesFound"}
        buttons={constantModalLabels.duplicate.buttons}
        closeModal={handleDuplicatesModalClose}
        header={constantModalLabels.duplicate.header}
        labels={constantModalLabels.duplicate.messages}
      />
      <ModalWidget
        open={modalOpen === "removeDuplicates"}
        buttons={constantModalLabels.removeDuplicates.buttons}
        closeModal={closeRemoveDuplicatesModal}
        header={constantModalLabels.removeDuplicates.header}
        labels={constantModalLabels.removeDuplicates.messages}
      />
      <ModalWidget
        open={openChangelog}
        buttons={["Close"]}
        width={900}
        closeModal={() => setOpenChangelog(false)}
        header={`Changelog for ${selectedWell}`}
        labels={
          changelog[selectedWell] && changelog[selectedWell].length > 0
            ? changelog[selectedWell].map((message) => message)
            : ["No changes found."]
        }
      />
      <ModalWidget
        open={creditUsageAlert}
        labels={["This re-analysis will consume 1 analysis credit."]}
        closeModal={() => {
          setCreditUsageAlert(false);
        }}
        header={"Attention!"}
      />
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
