import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import DropDownWidget from "../basicWidgets/DropDownWidget";
import WaveformGraph from "./InteractiveWaveformGraph";
import { deepCopy } from "@/utils/generic";
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
import { useWaveformData } from "@/components/interactiveAnalysis/useWaveformData";

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
      "Interactive analysis requires a newer version of Pulse3D than the version originally used on this recording. Peaks and valleys may be slightly different.",
      "Please re-analyze this recording using a Pulse3D version greater than 0.28.3.",
    ],
    buttons: ["Close"],
  },
  dataFound: {
    header: "Important!",
    messages: ["Previous changes have been found for this analysis.", "Do you want to use it or start over?"],
    buttons: ["Start Over", "Use Existing Changes"],
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

const ACTIONS = {
  ADD: "add",
  UNDO: "undo",
  RESET: "reset",
};

const LOAD_STATUSES = {
  NOT_LOADED: "not_loaded",
  LOADING_EXISTING: "existing",
  LOADING_NEW: "new",
  LOADED: "loaded",
};

const getDefaultCustomAnalysisSettings = (wells) => {
  const customVals = {
    // add values that apply to all wells
    windowedAnalysisBounds: {
      start: null,
      end: null,
    },
  };
  // add per well values
  for (const well of wells) {
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

const getArraysForWells = (wells) => {
  const changelog = {};
  for (const well of wells) {
    changelog[well] = [];
  }
  return changelog;
};

const title = (s) => {
  return s.charAt(0).toUpperCase() + s.slice(1);
};

const formatFeatureName = (featureName) => {
  // Remove the 's' at the end so it's not plural in the changelog
  return title(featureName).slice(0, -1);
};

const formatFloat = (n) => {
  return n.toFixed(2);
};

const formatCoords = ([x, y]) => {
  return `[ ${formatFloat(x)}, ${formatFloat(y)} ]`;
};

export default function InteractiveWaveformModal({
  selectedJob,
  setOpenInteractiveAnalysis,
  numberOfJobsInUpload,
}) {
  // this hook gets waveform data no matter what first
  // a useEffect watching the error and loading states kicks off next step
  const { waveformData, featureIndices, getErrorState, getLoadingState } = useWaveformData(
    `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/waveform-data?upload_id=${selectedJob.uploadId}&job_id=${selectedJob.jobId}`
  );

  const { usageQuota } = useContext(AuthContext);
  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);

  const [loadStatus, setLoadStatus] = useState(LOAD_STATUSES.NOT_LOADED);
  const isLoading = loadStatus !== LOAD_STATUSES.LOADED;

  const [creditUsageAlert, setCreditUsageAlert] = useState(false);
  const [pulse3dVersionIdx, setPulse3dVersionIdx] = useState(0);
  const [filteredVersions, setFilteredVersions] = useState([]);
  const [deprecationNotice, setDeprecationNotice] = useState(false);
  const [pulse3dVersionEOLDate, setPulse3dVersionEOLDate] = useState("");
  const [nameOverride, setNameOverride] = useState();
  const [uploadInProgress, setUploadInProgress] = useState(false); // determines state of interactive analysis upload
  const [modalOpen, setModalOpen] = useState(false);
  const [modalLabels, setModalLabels] = useState(constantModalLabels.success);

  const [removeDupsChecked, setRemoveDupsChecked] = useState(false);
  const [removeDupsWarning, setRemoveDupsWarning] = useState(false);
  const [disableRemoveDupsCheckbox, setDisableRemoveDupsCheckbox] = useState(false);

  const [selectedWell, setSelectedWell] = useState("A1");

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
  const [customAnalysisSettings, setCustomAnalysisSettings] = useState({});
  // This only exists as a convenience for passing data down to WaveformGraph. It's a copy of customAnalysisSettings with only the data relevant for the selected well
  const [customAnalysisSettingsForWell, setCustomAnalysisSettingsForWell] = useState();
  // TODO could probably combine customAnalysisSettingsChanges and changelog
  const [customAnalysisSettingsChanges, setCustomAnalysisSettingsChanges] = useState({});
  const [changelog, setChangelog] = useState({});
  const [openChangelog, setOpenChangelog] = useState(false);

  const updateCustomAnalysisSettings = (newCustomAnalysisSettings) => {
    newCustomAnalysisSettings = deepCopy(newCustomAnalysisSettings);

    for (const well of Object.keys(waveformData)) {
      if (well in newCustomAnalysisSettings) {
        newCustomAnalysisSettings[well].filteredFeatureIndices = filterAndSortFeatures(
          originalAnalysisData.coordinates[well],
          newCustomAnalysisSettings.windowedAnalysisBounds,
          newCustomAnalysisSettings[well]
        );
        newCustomAnalysisSettings[well].duplicateFeatureIndices = checkDuplicates(
          newCustomAnalysisSettings[well].filteredFeatureIndices
        );
      }
    }
    setCustomAnalysisSettings(newCustomAnalysisSettings);
  };

  const resetWellChanges = () => {
    customAnalysisSettingsInitializers.featureIndices(selectedWell, "peaks", baseData[selectedWell][0]);
    customAnalysisSettingsInitializers.featureIndices(selectedWell, "valleys", baseData[selectedWell][1]);
    setBothLinesToDefault(selectedWell);
  };

  // setChangelog and setCustomAnalysisSettingsChanges should not be called directly, use this instead so they are always handled together.
  // This should also only be used for changes that only apply to the currently selected well. Global changes should be handled separately
  const handleChangeForCurrentWell = (actionType, newWellSettings = null, newChangelogMsg = null) => {
    const changelogCopy = deepCopy(changelog);
    const changelogCopyForWell = changelogCopy[selectedWell];
    const customAnalysisSettingsChangesCopy = deepCopy(customAnalysisSettingsChanges);
    const customAnalysisSettingsChangesCopyForWell = customAnalysisSettingsChangesCopy[selectedWell];
    const customAnalysisSettingsCopy = deepCopy(customAnalysisSettings);

    let newCustomAnalysisSettings;
    if (actionType === ACTIONS.ADD) {
      customAnalysisSettingsChangesCopyForWell.push(newWellSettings);
      changelogCopyForWell.push(newChangelogMsg);
      newCustomAnalysisSettings = {
        ...customAnalysisSettingsCopy,
        [selectedWell]: newWellSettings,
      };
    } else if (actionType === ACTIONS.RESET || changelogCopyForWell.length <= 1) {
      customAnalysisSettingsChangesCopyForWell.splice(0, customAnalysisSettingsChangesCopyForWell.length);
      changelogCopyForWell.splice(0, changelogCopyForWell.length);
      resetWellChanges();
    } else {
      // UNDO with at least 2 changes in the changelog at the time of the action, so reset does not need to be handled here
      customAnalysisSettingsChangesCopyForWell.splice(customAnalysisSettingsChangesCopyForWell.length - 1, 1);
      changelogCopyForWell.splice(changelogCopyForWell.length - 1, 1);
      newCustomAnalysisSettings = {
        ...customAnalysisSettingsCopy,
        [selectedWell]: customAnalysisSettingsChangesCopyForWell.slice(-1)[0],
      };
    }
    if (newCustomAnalysisSettings) {
      updateCustomAnalysisSettings(newCustomAnalysisSettings);
    }
    updateChangelog(changelogCopy, customAnalysisSettingsChangesCopy);
  };

  const updateChangelog = (changelogCopy, customAnalysisSettingsChangesCopy) => {
    setChangelog(changelogCopy);
    setCustomAnalysisSettingsChanges(customAnalysisSettingsChangesCopy);
    // need to update this whenever changelog is updated
    setDisableRemoveDupsCheckbox(isRemoveDuplicatesDisabled(changelogCopy));
  };

  const customAnalysisSettingsInitializers = {
    windowBounds: (initialBounds) => {
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        windowedAnalysisBounds: deepCopy(initialBounds),
      });
    },
    featureIndices: (well, featureName, initialIndices) => {
      if (well in customAnalysisSettings) {
        const wellSettings = customAnalysisSettings[well];
        wellSettings.allFeatureIndices[featureName] = deepCopy(initialIndices);
        updateCustomAnalysisSettings({
          ...customAnalysisSettings,
          [well]: wellSettings,
        });
      }
    },
    thresholdEndpoints: (well, featureName, initialValue) => {
      if (well in customAnalysisSettings) {
        const wellSettings = customAnalysisSettings[well];
        wellSettings.thresholdEndpoints[featureName] = {
          y1: initialValue,
          y2: initialValue,
        };
        updateCustomAnalysisSettings({
          ...customAnalysisSettings,
          [well]: wellSettings,
        });
      }
    },
  };

  const customAnalysisSettingsUpdaters = {
    // Global changes are not tracked in the changelog
    setWindowBounds: (newBounds) => {
      updateCustomAnalysisSettings({
        ...customAnalysisSettings,
        windowedAnalysisBounds: {
          ...customAnalysisSettings.windowedAnalysisBounds,
          ...newBounds,
        },
      });
    },
    // These functions will always update the changelog
    addFeature: (featureName, timepoint) => {
      const wellSettings = customAnalysisSettings[selectedWell];
      const wellFeatureIndices = wellSettings.allFeatureIndices[featureName];

      const idxToAdd = wellWaveformData.findIndex(
        (coord) => Number(coord[0].toFixed(2)) === Number(timepoint.toFixed(2))
      );
      wellFeatureIndices.push(idxToAdd);

      const changelogMsg = `${formatFeatureName(featureName)} at ${formatCoords(
        wellWaveformData[idxToAdd]
      )} was added.`;

      handleChangeForCurrentWell(ACTIONS.ADD, wellSettings, changelogMsg);
    },
    deleteFeature: (featureName, idxToDelete) => {
      const wellSettings = customAnalysisSettings[selectedWell];
      const wellFeatureIndices = wellSettings.allFeatureIndices[featureName];

      const targetIdx = wellFeatureIndices.indexOf(idxToDelete);
      if (targetIdx === -1) return;
      wellFeatureIndices.splice(targetIdx, 1);

      const changelogMsg = `${formatFeatureName(featureName)} at ${formatCoords(
        wellWaveformData[idxToDelete]
      )} was removed.`;

      handleChangeForCurrentWell(ACTIONS.ADD, wellSettings, changelogMsg);
    },
    moveFeature: (featureName, originalIdx, newIdx) => {
      const wellSettings = customAnalysisSettings[selectedWell];
      const wellFeatureIndices = wellSettings.allFeatureIndices[featureName];

      const targetIdx = wellFeatureIndices.indexOf(originalIdx);
      if (targetIdx === -1) return;
      wellFeatureIndices.splice(targetIdx, 1, newIdx);

      const changelogMsg = `${formatFeatureName(featureName)} at ${formatCoords(
        wellWaveformData[originalIdx]
      )} was moved to ${formatCoords(wellWaveformData[newIdx])}.`;

      handleChangeForCurrentWell(ACTIONS.ADD, wellSettings, changelogMsg);
    },
    setThresholdEndpoints: (featureName, newEndpoints) => {
      const wellSettings = customAnalysisSettings[selectedWell];

      wellSettings.thresholdEndpoints[featureName] = {
        ...wellSettings.thresholdEndpoints[featureName],
        ...newEndpoints,
      };

      let changelogMsg = `${formatFeatureName(featureName)} Line `;
      if (newEndpoints.y1) {
        if (newEndpoints.y2) {
          changelogMsg += `Endpoints changed to Y1: ${formatFloat(newEndpoints.y1)} and Y2: ${formatFloat(
            newEndpoints.y2
          )}.`;
        } else {
          changelogMsg += `Y1 changed to ${formatFloat(newEndpoints.y1)}.`;
        }
      } else {
        changelogMsg += `Y2 changed to ${formatFloat(newEndpoints.y2)}.`;
      }

      handleChangeForCurrentWell(ACTIONS.ADD, wellSettings, changelogMsg);
    },
  };

  // One-time setup for component.
  // Currently just need to set the available pulse3d versions and check the current usage of the user
  useEffect(() => {
    if (usageQuota && usageQuota.limits && numberOfJobsInUpload >= 2 && usageQuota.limits.jobs !== -1) {
      setCreditUsageAlert(true);
    }
  }, []);

  // Update baseData anytime the remove dups checkbox state changes, except when set during load of existing changes
  useEffect(() => {
    if (loadStatus === LOAD_STATUSES.LOADING_EXISTING) {
      return;
    }
    if (removeDupsChecked) {
      const baseDataCopy = deepCopy(baseData);
      for (const well in baseDataCopy) {
        const { duplicateFeatureIndices } = customAnalysisSettings[well];
        baseDataCopy[well][0] = removeDups(baseDataCopy[well][0], duplicateFeatureIndices.peaks);
        baseDataCopy[well][1] = removeDups(baseDataCopy[well][1], duplicateFeatureIndices.valleys);
      }
      setBaseData(baseDataCopy);
    } else if (originalAnalysisData.featuresForWells) {
      // if unchecked, revert back to previous peaks and valleys
      setBaseData(originalAnalysisData.featuresForWells);
    }
  }, [removeDupsChecked]);

  // Update the custom peaks and valleys correctly after baseData is updated.
  // Currently baseData will only be updated when it is initially set for all wells, when the remove dups checkbox state changes (in the useEffect above),
  // and when loading existing data.
  useEffect(() => {
    if (loadStatus === LOAD_STATUSES.LOADING_EXISTING) {
      return;
    }
    for (const well of Object.keys(waveformData)) {
      if (baseData[well]) {
        customAnalysisSettingsInitializers.featureIndices(well, "peaks", baseData[well][0]);
        customAnalysisSettingsInitializers.featureIndices(well, "valleys", baseData[well][1]);
      }
    }
  }, [baseData]);

  // A spinner is displayed until the waveform data for the currently selected well is loaded.
  // This switches from the spinner to the WaveformGraph once that happens, as well as setting the default
  // threshold lines if they aren't already set (i.e. loaded from sessionStorage)
  useEffect(() => {
    switch (loadStatus) {
      case LOAD_STATUSES.LOADING_NEW: {
        for (const well of Object.keys(waveformData)) {
          setBothLinesToDefault(well);
        }
        // fall through expected here
      }
      case LOAD_STATUSES.LOADING_EXISTING: {
        setLoadStatus(LOAD_STATUSES.LOADED);
      }
    }
  }, [loadStatus]);

  // update customAnalysisSettingsForWell whenever customAnalysisSettings or the currently selected well changes
  useEffect(() => {
    if (selectedWell in customAnalysisSettings)
      setCustomAnalysisSettingsForWell(
        // Tanner (6/1/23): Copying just to be safe
        deepCopy({
          windowedAnalysisBounds: customAnalysisSettings.windowedAnalysisBounds,
          featureIndices: customAnalysisSettings[selectedWell].filteredFeatureIndices,
          duplicateIndices: customAnalysisSettings[selectedWell].duplicateFeatureIndices,
          thresholdEndpoints: customAnalysisSettings[selectedWell].thresholdEndpoints,
        })
      );
  }, [customAnalysisSettings, selectedWell]);

  const handleWaveformData = async () => {
    try {
      setSelectedWell(Object.keys(waveformData)[0]);
      setCustomAnalysisSettingsChanges(getArraysForWells(Object.keys(waveformData)));
      setChangelog(getArraysForWells(Object.keys(waveformData)));
      setBaseData(featureIndices);

      customAnalysisSettings = getDefaultCustomAnalysisSettings(Object.keys(waveformData));
      setCustomAnalysisSettings(customAnalysisSettings);

      // original data is set and never changed to hold original state in case of reset
      originalAnalysisData = { featuresForWells: featureIndices, coordinates: waveformData };
      setOriginalAnalysisData(originalAnalysisData);

      const { start_time, end_time } = selectedJob.analysisParams;
      const newTimepointRange = {
        min: start_time || Math.min(...waveformData[Object.keys(waveformData)[0]].map((coords) => coords[0])),
        max: end_time || Math.max(...waveformData[Object.keys(waveformData)[0]].map((coords) => coords[0])),
      };
      setTimepointRange(newTimepointRange);
      customAnalysisSettingsInitializers.windowBounds({
        start: newTimepointRange.min,
        end: newTimepointRange.max,
      });

      // won't be present for older recordings or if no replacement was ever given
      if ("nameOverride" in selectedJob) setNameOverride(selectedJob.nameOverride);

      if (!semverGte(selectedJob.analysisParams.pulse3d_version, "0.28.3")) {
        setModalLabels(constantModalLabels.oldPulse3dVersion);
        setModalOpen("pulse3dWarning");
      }

      setLoadStatus(LOAD_STATUSES.LOADING_NEW);
    } catch (e) {
      console.log("ERROR handling waveform data:", e);
      // open error modal and kick users back to /uploads page if random  error
      setModalLabels(constantModalLabels.error);
      setModalOpen("status");
    }
  };

  const saveChanges = () => {
    try {
      const saveData = {
        baseData,
        removeDupsChecked,
        changelog,
        customAnalysisSettingsChanges,
        customAnalysisSettings,
      };
      sessionStorage.setItem(selectedJob.jobId, JSON.stringify(saveData));
    } catch (e) {
      console.log("ERROR saving changes:", e);
    }
  };

  const loadExistingData = () => {
    const jsonData = sessionStorage.getItem(selectedJob.jobId);
    const existingData = JSON.parse(jsonData);
    setCustomAnalysisSettings(existingData.customAnalysisSettings);
    updateChangelog(existingData.changelog, existingData.customAnalysisSettingsChanges);
    setRemoveDupsChecked(existingData.removeDupsChecked);
    setBaseData(existingData.baseData);
    setLoadStatus(LOAD_STATUSES.LOADING_EXISTING);
  };

  const handleWellSelection = async (idx) => {
    const wellName = Object.keys(waveformData)[idx];
    if (wellName !== selectedWell) {
      setSelectedWell(wellName);
    }
  };

  const postNewJob = async () => {
    try {
      setUploadInProgress(true);

      const filteredFeatures = {};
      for (const well in customAnalysisSettings) {
        if (!Object.keys(waveformData).includes(well)) continue; // ignore global changes
        const { peaks, valleys } = customAnalysisSettings[well].filteredFeatureIndices;
        filteredFeatures[well] = [peaks, valleys];
      }

      const prevPulse3dVersion = selectedJob.analysisParams.pulse3d_version;
      const { start: startTime, end: endTime } = customAnalysisSettings.windowedAnalysisBounds;

      // reassign new peaks and valleys if different
      const requestBody = {
        ...selectedJob.analysisParams,
        upload_id: selectedJob.uploadId,
        peaks_valleys: filteredFeatures,
        start_time: startTime === timepointRange.min ? null : startTime,
        end_time: endTime === timepointRange.max ? null : endTime,
        version: filteredVersions[pulse3dVersionIdx],
        previous_version: prevPulse3dVersion,
      };

      // only add for versions greater than 0.32.2
      if (semverGte(prevPulse3dVersion, "0.32.2")) {
        requestBody.name_override = nameOverride === "" ? null : nameOverride;
      }

      const jobResponse = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs`, {
        method: "POST",
        body: JSON.stringify(requestBody),
      });

      if (jobResponse.status !== 200) {
        console.log("ERROR posting new job:", await jobResponse.json());
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
      console.log("ERROR posting new job:", e);
      setModalLabels(constantModalLabels.error);
      setUploadInProgress(false);
      setModalOpen("status");
    }
  };

  const handleModalClose = async (i) => {
    // close IA if error status warning or old pulse3d warning modals are closed
    if (modalOpen === "status" || modalOpen === "pulse3dWarning") {
      setOpenInteractiveAnalysis(false);
    } else {
      await handleWaveformData();
      if (i === 1) {
        loadExistingData();
        // remove existing record if it was loaded
        sessionStorage.removeItem(selectedJob.jobId);
      }
    }
    // close modal
    setModalOpen(false);
  };

  const handleVersionSelect = (idx) => {
    const selectedVersionMetadata = metaPulse3dVersions.filter(
      (version) => version.version === pulse3dVersions[idx]
    )[0];

    setPulse3dVersionEOLDate(
      `Version ${selectedVersionMetadata.version} will be removed ${
        selectedVersionMetadata.end_of_life_date || "soon"
      }.`
    );

    setDeprecationNotice(selectedVersionMetadata.state === "deprecated");
    setPulse3dVersionIdx(idx);
  };

  const handleRunAnalysis = () => {
    const wellsWithDups = [];
    Object.keys(customAnalysisSettings).map((well) => {
      if (!Object.keys(waveformData).includes(well)) return; // ignore global changes
      const { duplicateFeatureIndices } = customAnalysisSettings[well];
      const { peaks, valleys } = duplicateFeatureIndices;
      if (peaks.length > 0 || valleys.length > 0) wellsWithDups.push(well);
    });

    if (wellsWithDups.length > 0) {
      const wellsWithDupsString = wellsWithDups.join(", ");
      constantModalLabels.duplicate.messages.splice(1, 1, wellsWithDupsString);
      setModalOpen("duplicatesFound");
    } else {
      postNewJob();
    }
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

  const calculateYLimit = ({ y1, y2 }, windowedAnalysisBounds, markerX) => {
    const { start: x1, end: x2 } = windowedAnalysisBounds;
    const slope = (y2 - y1) / (x2 - x1);
    return y1 + slope * (markerX - x1);
  };

  const findInitialThresholdForFeature = (well, featureType) => {
    const { coordinates, featuresForWells } = originalAnalysisData;
    const { max, min } = timepointRange;

    const compare = (a, b) => {
      return b == null || (featureType === "peaks" ? a < b : a > b);
    };

    const featureIdx = featureType === "peaks" ? 0 : 1;
    const wellSpecificFeatures = featuresForWells[well][featureIdx];
    const wellSpecificCoords = coordinates[well];

    let currentTresholdY = null;

    // consider when no features were found in a well
    if (wellSpecificCoords && wellSpecificFeatures.length > 0) {
      wellSpecificFeatures.map((featureIdx) => {
        const [testX, testY] = wellSpecificCoords[featureIdx];
        // only use features inside windowed analysis times
        const isLessThanEndTime = !max || testX <= max;
        const isGreaterThanStartTime = !min || testX >= min;
        // filter for features inside windowed time
        if (compare(testY, currentTresholdY) && isGreaterThanStartTime && isLessThanEndTime) {
          currentTresholdY = testY;
        }
      });
    }

    return currentTresholdY;
  };

  const setBothLinesToDefault = (well) => {
    customAnalysisSettingsInitializers.thresholdEndpoints(
      well,
      "peaks",
      findInitialThresholdForFeature(well, "peaks")
    );
    customAnalysisSettingsInitializers.thresholdEndpoints(
      well,
      "valleys",
      findInitialThresholdForFeature(well, "valleys")
    );
  };

  const filterAndSortFeatures = (
    wellCoords,
    windowedAnalysisBounds,
    { allFeatureIndices, thresholdEndpoints }
  ) => {
    allFeatureIndices = deepCopy(allFeatureIndices);

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

          let isFeatureWithinThreshold;
          if (thresholdEndpoints[featureType].y1 == null || thresholdEndpoints[featureType].y2 == null) {
            isFeatureWithinThreshold = true;
          } else {
            const featureThresholdY = calculateYLimit(
              thresholdEndpoints[featureType],
              windowedAnalysisBounds,
              featureMarkerX
            );
            isFeatureWithinThreshold =
              featureType === "peaks"
                ? featureMarkerY >= featureThresholdY
                : featureMarkerY <= featureThresholdY;
          }

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
    // Should be disabled if the data for the current well is loading or if any changes have been made on any well
    return isLoading || Object.keys(changelogCopy).some((well) => changelogCopy[well].length > 0);
  };

  // ENTRYPOINT
  // defined last so that everything required for it already exists
  // Luci (12-14-2022) this component gets mounted twice and we don't want this expensive function to request waveform data to be called twice. This ensures it is only called once per job selection
  useEffect(() => {
    if (getErrorState) {
      // open error modal and kick users back to /uploads page if random  error
      setModalLabels(constantModalLabels.error);
      setModalOpen("status");
    } else if (!getLoadingState) {
      const compatibleVersions = pulse3dVersions.filter((v) => {
        if (Object.keys(waveformData).length === 24) {
          return true;
        } else {
          const minVersion = Object.keys(waveformData).length < 24 ? "0.32.2" : "0.33.13";
          return semverGte(v, minVersion);
        }
      });

      setFilteredVersions([...compatibleVersions]);

      const data = sessionStorage.getItem(selectedJob.jobId); // returns null if key doesn't exist in storage
      if (data) {
        // if data is found in sessionStorage then do ?
        setModalLabels(constantModalLabels.dataFound);
        setModalOpen("dataFound");
      } else {
        // if no data stored, then need to retrieve from server
        handleWaveformData();
      }
    }
  }, [getErrorState, getLoadingState]);

  return (
    <Container>
      <HeaderContainer>Interactive Waveform Analysis</HeaderContainer>
      <WellDropdownContainer>
        <WellDropdownLabel>Select Well:</WellDropdownLabel>
        <DropDownWidget
          options={Object.keys(waveformData)}
          handleSelection={handleWellSelection}
          disabled={isLoading}
          reset={selectedWell === Object.keys(waveformData)[0]}
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
              undo: () => handleChangeForCurrentWell(ACTIONS.UNDO),
              reset: () => handleChangeForCurrentWell(ACTIONS.RESET),
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
              options={filteredVersions.map((version) => {
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
