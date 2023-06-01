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
  width: 360px;
  justify-content: space-between;
`;

const ParamLabel = styled.span`
  line-height: 2;
  font-size: 16px;
  white-space: nowrap;
  padding-right: 15px;
  display: flex;
  align-items: center;
  cursor: default;
`;

const GraphContainer = styled.div`
  height: 415px;
  border-radius: 7px;
  background-color: var(--med-gray);
  position: relative;
  width: 1350px;
  margin-top: 4%;
  overflow: hidden;
  padding: 0px 15px;
  display: flex;
  flex-direction: column;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const SpinnerContainer = styled.div`
  height: 100%;
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: center;
`;
const ButtonContainer = styled.div`
  position: relative;
  height: 50px;
  width: 100%;
  display: flex;
  justify-content: flex-end;
`;

const ErrorLabel = styled.div`
  position: relative;
  width: 80%;
  height: 40px;
  align-items: center;
  color: red;
  font-style: italic;
  display: flex;
  justify-content: flex-end;
`;
const TooltipText = styled.span`
  font-size: 15px;
`;

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
};

const wellNames = Array(24)
  .fill()
  .map((_, idx) => twentyFourPlateDefinition.getWellNameFromIndex(idx));

const getDefaultFeatures = () => {
  const features = {};
  for (const well of wellNames) {
    features[well] = [null, null];
  }
  return features;
};

const getDefaultCustomAnalysisSettings = () => {
  const customVals = {
    // add values that apply to all wells
    windowAnalysisBounds: {
      start: null,
      end: null,
    },
  };
  // add per well values
  for (const well of wellNames) {
    customVals[well] = {
      featureIndices: {
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
  const [duplicateModalOpen, setDuplicateModalOpen] = useState(false);

  const [selectedWell, setSelectedWell] = useState("A1");
  const wellIdx = twentyFourPlateDefinition.getWellIndexFromName(selectedWell);

  const [errorMessage, setErrorMessage] = useState(); // Tanner (5/25/23): seems unused at the moment, but leaving it here anyway

  const [originalAnalysisData, setOriginalAnalysisData] = useState({}); // original waveforms and peaks/valleys for each well from GET request, unedited
  const wellWaveformData = originalAnalysisData.coordinates
    ? originalAnalysisData.coordinates[selectedWell]
    : [];
  const [timepointRange, setTimepointRange] = useState({
    // This is a copy of the max/min timepoints of the data. Windowed analysis start/stop times are set in editableStartEndTimes.
    // Must be stored in its own state and not tied directly to the recording data because it will be set to the start/stop times of the job if
    // They were set
    min: null,
    max: null,
  });

  const [customAnalysisSettings, setCustomAnalysisSettings] = useState(getDefaultCustomAnalysisSettings());
  // This only exists as a convenience for passing data down to WaveformGraph. It's a copy of customAnalysisSettings with only the data relevant for the selected well
  const [customAnalysisSettingsForWell, setCustomAnalysisSettingsForWell] = useState({});

  // TODO remove these
  const [editablePeaksValleys, setEditablePeaksValleys] = useState(getDefaultFeatures()); // user edited peaks/valleys as changes are made, should get stored in localStorage
  const [peakValleyWindows, setPeakValleyWindows] = useState({}); // TODO see if this can be removed in place of the endpoints, or at least changed to the default values. Will also need to figure out how to handle the changelog entries once this is removed
  const [editableStartEndTimes, setEditableStartEndTimes] = useState({
    startTime: null,
    endTime: null,
  });
  // state for peaks
  const [peakY1, setPeakY1] = useState([]);
  const [peakY2, setPeakY2] = useState([]);
  // state for valleys
  const [valleyY1, setValleyY1] = useState([]);
  const [valleyY2, setValleyY2] = useState([]);

  const [changelog, setChangelog] = useState({});
  const [openChangelog, setOpenChangelog] = useState(false);
  const [undoing, setUndoing] = useState(false);

  const customAnalysisSettingsInitializers = {
    windowBounds: (initialBounds) => {
      setCustomAnalysisSettings({
        ...customAnalysisSettings,
        windowAnalysisBounds: JSON.parse(JSON.stringify(initialBounds)),
      });
    },
    featureIndices: (well, featureName, initialIndices) => {
      const wellSettings = customAnalysisSettings[well];
      wellSettings.featureIndices[featureName] = JSON.parse(JSON.stringify(initialIndices));
      setCustomAnalysisSettings({
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
      setCustomAnalysisSettings({
        ...customAnalysisSettings,
        [well]: wellSettings,
      });
    },
  };

  const customAnalysisSettingsUpdaters = {
    // These functions will always update the changelog
    setWindowBound: (boundName, boundValue) => {
      setCustomAnalysisSettings({
        ...customAnalysisSettings,
        [boundName]: boundValue,
      });
      // TODO update changelog
    },
    addFeature: (featureName, timepoint) => {
      const wellSettings = customAnalysisSettings[selectedWell];
      const wellFeatureIndices = wellSettings.featureIndices[featureName];
      const idxToAdd = wellWaveformData.findIndex(
        (coord) => Number(coord[0].toFixed(2)) === Number(timepoint.toFixed(2))
      );

      wellFeatureIndices.push(idxToAdd);
      setCustomAnalysisSettings({
        ...customAnalysisSettings,
        [selectedWell]: wellSettings,
      });
      // TODO update changelog
    },
    deleteFeature: (featureName, idxToDelete) => {
      const wellSettings = customAnalysisSettings[selectedWell];
      const wellFeatureIndices = wellSettings.featureIndices[featureName];

      const targetIdx = wellFeatureIndices.indexOf(idxToDelete);
      if (targetIdx === -1) return;

      wellFeatureIndices.splice(targetIdx, 1);
      setCustomAnalysisSettings({
        ...customAnalysisSettings,
        [selectedWell]: wellSettings,
      });
      // TODO update changelog
    },
    moveFeature: (featureName, originalIdx, newIdx) => {
      const wellSettings = customAnalysisSettings[selectedWell];
      const wellFeatureIndices = wellSettings.featureIndices[featureName];

      const targetIdx = wellFeatureIndices.indexOf(originalIdx);
      if (targetIdx === -1) return;

      wellFeatureIndices.splice(targetIdx, 1, newIdx);
      setCustomAnalysisSettings({
        ...customAnalysisSettings,
        [selectedWell]: wellSettings,
      });
      // TODO update changelog
    },
    setThresholdEndpoint: (featureName, endpointName, newValue) => {
      const wellSettings = customAnalysisSettings[selectedWell];

      wellSettings.thresholdEndpoints[featureName][endpointName] = newValue;
      setCustomAnalysisSettings({
        ...customAnalysisSettings,
        [well]: wellSettings,
      });
      // TODO update changelog
    },
  };

  useEffect(() => {
    const compatibleVersions = pulse3dVersions.filter((v) => semverGte(v, "0.28.3"));
    setFilteredVersions([...compatibleVersions]);
    if (usageQuota && usageQuota.limits && numberOfJobsInUpload >= 2 && usageQuota.limits.jobs !== -1) {
      setCreditUsageAlert(true);
    }
  }, []);

  useEffect(() => {
    // updates changelog when peaks/valleys and start/end times change
    if (undoing) {
      setUndoing(false);
    } else {
      updateChangelog();
    }
  }, [editableStartEndTimes, peakValleyWindows, peakY1, peakY2, valleyY1, valleyY2]);

  useEffect(() => {
    if (wellWaveformData.length > 0) {
      setIsLoading(false);
    }
  }, [wellWaveformData]);

  useEffect(() => {
    if (
      // check if these are empty
      [peakY1, peakY2, valleyY1, valleyY2].filter((arr) => arr[wellIdx] == null).length > 0 &&
      peakValleyWindows[selectedWell]
    ) {
      setBothLinesToDefault();
    }
  }, [peakValleyWindows]);

  useEffect(() => {
    setCustomAnalysisSettingsForWell(
      JSON.parse(
        JSON.stringify({
          windowAnalysisBounds: customAnalysisSettings.windowAnalysisBounds,
          ...customAnalysisSettings[selectedWell],
        })
      )
    );
  }, [customAnalysisSettings, selectedWell]);

  const getNewData = async () => {
    await getWaveformData(true, "A1");
  };

  const getWaveformData = async (peaksValleysNeeded, well) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/waveform-data?upload_id=${selectedJob.uploadId}&job_id=${selectedJob.jobId}&peaks_valleys=${peaksValleysNeeded}&well_name=${well}`
      );
      if (response.status !== 200) throw Error();

      const res = await response.json();
      if (res.error) throw Error();

      if (!("coordinates" in originalAnalysisData)) {
        originalAnalysisData = {
          peaksValleys: res.peaks_valleys, // TODO rename this
          coordinates: {},
        };
      }

      const { coordinates, peaks_valleys: peaksValleys } = res;
      // original data is set and never changed to hold original state in case of reset
      originalAnalysisData.coordinates[well] = coordinates;
      setOriginalAnalysisData(originalAnalysisData);

      if (peaksValleysNeeded) {
        customAnalysisSettingsInitializers.featureIndices(well, "peaks", peaksValleys[well][0]);
        customAnalysisSettingsInitializers.featureIndices(well, "valleys", peaksValleys[well][1]);

        const { start_time, end_time } = selectedJob.analysisParams;
        const newTimepointRange = {
          min: start_time || Math.min(...coordinates.map((coords) => coords[0])),
          max: end_time || Math.max(...coordinates.map((coords) => coords[0])),
        };
        setTimepointRange(newTimepointRange);
        setEditableStartEndTimes({
          startTime: newTimepointRange.min,
          endTime: newTimepointRange.max,
        });
        // won't be present for older recordings or if no replacement was ever given
        if ("nameOverride" in selectedJob) setNameOverride(selectedJob.nameOverride);
      }

      setInitialPeakValleyWindows(well);

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

  // TODO remove default value here
  const checkDuplicates = (well = selectedWell) => {
    // These should already be filtered
    const { peaks, valleys } = customAnalysisSettings[well].featureIndices;

    // TODO clean this up

    // create list with all features in order
    const features = [];
    for (const idx of peaks) {
      features.push({ type: "peak", idx });
    }
    for (const idx of valleys) {
      features.push({ type: "valley", idx });
    }
    features.sort((a, b) => a.idx - b.idx);

    const duplicates = [];
    for (let i = 1; i < features.length; i++) {
      const [prev, curr, next] = features.slice(i - 1, i + 2);
      if ((curr && curr.type === prev.type) || (next && next.type === curr.type)) {
        duplicates.push(curr.idx);
      }
    }

    return duplicates;
  };

  const setInitialPeakValleyWindows = (well) => {
    const pvCopy = JSON.parse(JSON.stringify(peakValleyWindows));

    pvCopy[well] = {
      minPeaks: findLowestPeak(well),
      maxValleys: findHighestValley(well),
    };

    setPeakValleyWindows(pvCopy);
  };

  const findLowestPeak = (well) => {
    const { coordinates, peaksValleys } = originalAnalysisData;
    const { startTime, endTime } = editableStartEndTimes;
    // arbitrarily set to first peak
    const wellSpecificPeaks = peaksValleys[well][0];
    const wellSpecificCoords = coordinates[well];

    // consider when no peaks or valleys were found in a well
    if (wellSpecificCoords && wellSpecificPeaks.length > 0) {
      let lowest = wellSpecificPeaks[0];

      wellSpecificPeaks.map((peak) => {
        const yCoord = wellSpecificCoords[peak][1];
        const peakToCompare = wellSpecificCoords[lowest][1];
        // only use peaks inside windowed analysis times
        const timeOfPeak = wellSpecificCoords[peak][0];
        const isLessThanEndTime = !endTime || timeOfPeak <= endTime;
        const isGreaterThanStartTime = !startTime || timeOfPeak >= startTime;
        // filter for peaks inside windowed time
        if (yCoord < peakToCompare && isGreaterThanStartTime && isLessThanEndTime) lowest = peak;
      });

      // return  y coordinate of lowest peak
      return wellSpecificCoords[lowest][1];
    }
  };

  const findHighestValley = (well) => {
    const { coordinates, peaksValleys } = originalAnalysisData;
    const { startTime, endTime } = editableStartEndTimes;
    // arbitrarily set to first valley
    const wellSpecificValleys = peaksValleys[well][1];
    const wellSpecificCoords = coordinates[well];

    // consider when no peaks or valleys were found in a well
    if (wellSpecificCoords && wellSpecificValleys.length > 0) {
      let highest = wellSpecificValleys[0];

      wellSpecificValleys.map((valley) => {
        const yCoord = wellSpecificCoords[valley][1];
        const valleyToCompare = wellSpecificCoords[highest][1];

        // only use valleys inside windowed analysis times
        const timeOfValley = wellSpecificCoords[valley][0];
        const isLessThanEndTime = !endTime || timeOfValley <= endTime;
        const isGreaterThanStartTime = !startTime || timeOfValley >= startTime;

        if (yCoord > valleyToCompare && isLessThanEndTime && isGreaterThanStartTime) highest = valley;
      });

      // return  y coordinate of highest valley
      return wellSpecificCoords[highest][1];
    }
  };

  const resetStartEndTimes = () => {
    setEditableStartEndTimes({
      startTime: timepointRange.min,
      endTime: timepointRange.max,
    });
  };

  const loadExistingData = () => {
    // this happens very fast so not storing to react state the first call, see line 162 (? different line now)
    const jsonData = sessionStorage.getItem(selectedJob.jobId);
    const existingData = JSON.parse(jsonData);
    // TODO test this
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
    const pvWindowCopy = JSON.parse(JSON.stringify(peakValleyWindows));
    const originalFeaturesForWell = originalAnalysisData.peaksValleys[selectedWell];
    changelogCopy[selectedWell] = [];
    pvWindowCopy[selectedWell] = {
      minPeaks: findLowestPeak(selectedWell),
      maxValleys: findHighestValley(selectedWell),
    };
    // reset state
    resetStartEndTimes();
    customAnalysisSettingsInitializers.featureIndices(selectedWell, "peaks", originalFeaturesForWell[0]);
    customAnalysisSettingsInitializers.featureIndices(selectedWell, "valleys", originalFeaturesForWell[1]);
    setChangelog(changelogCopy);
    setPeakValleyWindows(pvWindowCopy);
    setBothLinesToDefault();
  };
  const postNewJob = async () => {
    try {
      setUploadInProgress(true);

      // TODO check that this is formatted correctly, AND MAKE SURE TO SEND ALL WELLS
      const filteredPeaksValleys = customAnalysisSettings["A1"].featureIndices;
      const prevPulse3dVersion = selectedJob.analysisParams.pulse3d_version;
      // jobs run on pulse3d versions < 0.28.3 will not have a 0 timepoint so account for that here that 0.01 is still the first time point, not windowed
      const startTime =
        !semverGte(prevPulse3dVersion, "0.28.3") && editableStartEndTimes.startTime == 0.01
          ? null
          : editableStartEndTimes.startTime;

      // reassign new peaks and valleys if different
      const requestBody = {
        ...selectedJob.analysisParams,
        upload_id: selectedJob.uploadId,
        peaks_valleys: filteredPeaksValleys,
        start_time: startTime,
        end_time: editableStartEndTimes.endTime,
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
    // TODO TANNER update this
    // TODO handle if for some reason this is full and returns error
    sessionStorage.setItem(
      selectedJob.jobId,
      JSON.stringify({
        editableStartEndTimes,
        originalAnalysisData,
        changelog,
        peakValleyWindows,
        peakY1,
        peakY2,
        valleyY1,
        valleyY2,
      })
    );
  };

  const updateChangelog = () => {
    let changelogMessage;
    // changelog will have length of 0 if a user clicks undo all the way back to until initial state
    if (changelog[selectedWell] && changelog[selectedWell].length > 0) {
      // If Change log has changes
      const wellChanges = changelog[selectedWell];
      // Use snapshot of previus state to get changelog
      changelogMessage = getChangelogMessage(wellChanges[wellChanges.length - 1]);
    } else if (originalAnalysisData.peaksValleys && originalAnalysisData.peaksValleys[selectedWell]) {
      // If are no changes detected then add default values to first index of changelog
      const ogWellData = originalAnalysisData.peaksValleys[selectedWell];
      const maxValleyY = peakValleyWindows[selectedWell].maxValleys;
      const minPeakY = peakValleyWindows[selectedWell].minPeaks;
      const defaultChangelog = {
        peaks: ogWellData[0],
        valleys: ogWellData[1],
        startTime: timepointRange.min,
        endTime: timepointRange.max,
        pvWindow: {
          minPeaks: findLowestPeak(selectedWell),
          maxValleys: findHighestValley(selectedWell),
        },
        valleyYOne: maxValleyY,
        valleyYTwo: maxValleyY,
        peakYOne: minPeakY,
        peakYTwo: minPeakY,
      };
      changelogMessage = getChangelogMessage(defaultChangelog);
    }

    if (changelogMessage !== undefined) {
      addToChangelog(changelogMessage);
    }
  };

  const getChangelogMessage = ({
    peaks: peaksToCompare,
    valleys: valleysToCompare,
    startTime: startToCompare,
    endTime: endToCompare,
    pvWindow,
    valleyYOne: valleyY1ToCompare,
    valleyYTwo: valleyY2ToCompare,
    peakYOne: peakY1ToCompare,
    peakYTwo: peakY2ToCompare,
  }) => {
    // TODO
    return;
    const featuresForWell = editablePeaksValleys[selectedWell];

    let changelogMessage;
    const peaksMoved =
        JSON.stringify(peaksToCompare) !== JSON.stringify(featuresForWell[0]) &&
        peaksToCompare.length === featuresForWell[0].length, // added and deleted peaks is handled somewhere else
      valleysMoved =
        JSON.stringify(valleysToCompare) !== JSON.stringify(featuresForWell[1]) &&
        valleysToCompare.length === featuresForWell[1].length, // added and deleted peaks is handled somewhere else,
      startTimeDiff =
        startToCompare !== editableStartEndTimes.startTime &&
        editableStartEndTimes.startTime !== null &&
        startToCompare !== null,
      endTimeDiff =
        endToCompare !== editableStartEndTimes.endTime &&
        editableStartEndTimes.endTime !== null &&
        endToCompare !== null,
      windowedTimeDiff = startTimeDiff && endTimeDiff,
      minPeaksDiff = pvWindow.minPeaks !== peakValleyWindows[selectedWell].minPeaks,
      maxValleysDiff = pvWindow.maxValleys !== peakValleyWindows[selectedWell].maxValleys,
      isNewValleyY1 = isNewY(valleyY1ToCompare, valleyY1),
      isNewValleyY2 = isNewY(valleyY2ToCompare, valleyY2),
      isNewPeakY1 = isNewY(peakY1ToCompare, peakY1),
      isNewPeakY2 = isNewY(peakY2ToCompare, peakY2);

    if (peaksMoved) {
      const diffIdx = peaksToCompare.findIndex((peakIdx, i) => peakIdx !== featuresForWell[0][i]),
        oldPeakX = wellWaveformData[peaksToCompare[diffIdx]][0],
        oldPeakY = wellWaveformData[peaksToCompare[diffIdx]][1],
        newPeakX = wellWaveformData[featuresForWell[0][diffIdx]][0],
        newPeakY = wellWaveformData[featuresForWell[0][diffIdx]][1];

      changelogMessage = `Peak at [ ${oldPeakX.toFixed(2)}, ${oldPeakY.toFixed(
        2
      )} ] was moved to [ ${newPeakX.toFixed(2)}, ${newPeakY.toFixed(2)} ].`;
    } else if (valleysMoved) {
      const diffIdx = valleysToCompare.findIndex((valleyIdx, i) => valleyIdx !== featuresForWell[0][i]),
        oldValleyX = wellWaveformData[valleysToCompare[diffIdx]][0],
        oldValleyY = wellWaveformData[valleysToCompare[diffIdx]][1],
        newValleyX = wellWaveformData[featuresForWell[1][diffIdx]][0],
        newValleyY = wellWaveformData[featuresForWell[1][diffIdx]][1];

      changelogMessage = `Valley at [ ${oldValleyX.toFixed(2)}, ${oldValleyY.toFixed(
        2
      )} ] was moved to [ ${newValleyX.toFixed(2)}, ${newValleyY.toFixed(2)} ].`;
    } else if (windowedTimeDiff) {
      changelogMessage = `Start time was changed from ${startToCompare} to ${editableStartEndTimes.startTime} and end time was changed from ${endToCompare} to ${editableStartEndTimes.endTime}.`;
    } else if (startTimeDiff) {
      changelogMessage = `Start time was changed from ${startToCompare} to ${editableStartEndTimes.startTime}.`;
    } else if (endTimeDiff) {
      changelogMessage = `End time was changed from ${endToCompare} to ${editableStartEndTimes.endTime}.`;
    } else if (minPeaksDiff) {
      changelogMessage = `Minimum peaks window changed from ${pvWindow.minPeaks.toFixed(
        2
      )} to ${peakValleyWindows[selectedWell].minPeaks.toFixed(2)}`;
    } else if (maxValleysDiff) {
      changelogMessage = `Maximum valleys window changed from ${pvWindow.maxValleys.toFixed(
        2
      )} to ${peakValleyWindows[selectedWell].maxValleys.toFixed(2)}`;
    } else if (isNewValleyY1 && isNewValleyY2) {
      changelogMessage = `Valley Line moved ${valleyY1[wellIdx] - valleyY1ToCompare}`;
    } else if (isNewPeakY1 && isNewPeakY2) {
      changelogMessage = `Peak Line moved ${peakY1[wellIdx] - peakY1ToCompare}`;
    } else if (isNewValleyY1) {
      changelogMessage = `Valley Line Y1 switched to ${valleyY1[wellIdx]}`;
    } else if (isNewValleyY2) {
      changelogMessage = `Valley Line Y2 switched to ${valleyY2[wellIdx]}`;
    } else if (isNewPeakY1) {
      changelogMessage = `Peak Line Y1 switched to ${peakY1[wellIdx]}`;
    } else if (isNewPeakY2) {
      changelogMessage = `Peak Line Y2 switched to ${peakY2[wellIdx]}`;
    }
    return changelogMessage;
  };

  const addToChangelog = (message) => {
    // TODO update this
    if (!changelog[selectedWell]) changelog[selectedWell] = [];
    // if you don't deep copy state, later changes will affect change log entries here
    const { startTime, endTime } = JSON.parse(JSON.stringify(editableStartEndTimes));
    // const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
    const pvWindowCopy = JSON.parse(JSON.stringify(peakValleyWindows));

    changelog[selectedWell].push({
      peaks: peaksValleysCopy[selectedWell][0],
      valleys: peaksValleysCopy[selectedWell][1],
      startTime,
      endTime,
      message,
      pvWindow: pvWindowCopy[selectedWell],
      valleyYOne: valleyY1[wellIdx],
      valleyYTwo: valleyY2[wellIdx],
      peakYOne: peakY1[wellIdx],
      peakYTwo: peakY2[wellIdx],
    });

    setChangelog({ ...changelog });
  };

  const handleVersionSelect = (idx) => {
    const selectedVersionMetadata = metaPulse3dVersions.filter(
      (version) => version.version === pulse3dVersions[idx]
    )[0];
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
    // TODO fix this
    // Object.keys(editablePeaksValleys).map((well) => {
    //   // if any duplicates are present, push well into storage array to add to modal letting user know which wells are affected
    //   if (checkDuplicates(well).length > 0) wellsWithDups.push(well);
    // });

    if (wellsWithDups.length > 0) {
      const wellsWithDupsString = wellsWithDups.join(", ");
      constantModalLabels.duplicate.messages.splice(1, 1, wellsWithDupsString);
      setDuplicateModalOpen(true);
    } else {
      postNewJob();
    }
  };

  const undoLastChange = () => {
    if (changelog[selectedWell] && changelog[selectedWell].length > 0) {
      // undoing state tells the updateChangelog useEffect to not ignore the change and not as a new change
      setUndoing(true);
      // make copies so you control when state is updated
      const changesCopy = JSON.parse(JSON.stringify(changelog[selectedWell]));
      // const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
      const pvWindowCopy = JSON.parse(JSON.stringify(peakValleyWindows));
      const newWindowTimes = {};
      // remove step with latest changes
      changesCopy.pop();

      if (changesCopy.length > 0) {
        // grab state from the step before the undo step to set as current state
        const {
          peaks,
          valleys,
          startTime,
          endTime,
          pvWindow,
          valleyYOne,
          valleyYTwo,
          peakYOne,
          peakYTwo,
        } = changesCopy[changesCopy.length - 1];
        // set old peaks and valleys to well
        peaksValleysCopy[selectedWell] = [[...peaks], [...valleys]];
        pvWindowCopy[selectedWell] = pvWindow;
        newWindowTimes.startTime = startTime;
        newWindowTimes.endTime = endTime;
        setBothLinesToNew(peakYOne, peakYTwo, valleyYOne, valleyYTwo);
      } else {
        // if undoing the very first change, revert back to original state
        newWindowTimes.startTime = timepointRange.min;
        newWindowTimes.endTime = timepointRange.max;

        peaksValleysCopy[selectedWell] = originalAnalysisData.peaksValleys[selectedWell];
        pvWindowCopy[selectedWell] = {
          minPeaks: findLowestPeak(selectedWell),
          maxValleys: findHighestValley(selectedWell),
        };
        setBothLinesToDefault();
      }

      // needs to be reassigned to hold state
      changelog[selectedWell] = changesCopy;
      // update values to state to rerender graph
      setEditableStartEndTimes(newWindowTimes);
      // setEditablePeaksValleys(peaksValleysCopy);
      setPeakValleyWindows(pvWindowCopy);
      setChangelog(changelog);
    }
  };

  const pulse3dVersionGte = (version) => {
    return filteredVersions.length > 0 && semverGte(filteredVersions[pulse3dVersionIdx], version);
  };

  const handleDuplicatesModalClose = (isRunAnalysisOption) => {
    setDuplicateModalOpen(false);
    if (isRunAnalysisOption) {
      postNewJob();
    }
  };

  const calculateYLimit = (y1, y2, markerX) => {
    const slope = (y2 - y1) / (editableStartEndTimes.endTime - editableStartEndTimes.startTime);
    return y1 + slope * (markerX - editableStartEndTimes.startTime);
  };

  const assignNewArr = (data, newValue, setState) => {
    let newArr = [...data];
    newArr[wellIdx] = newValue;
    setState([...newArr]);
  };

  // TODO clean all this up
  const setBothLinesToDefault = () => {
    assignNewArr(peakY1, peakValleyWindows[selectedWell].minPeaks, setPeakY1);
    assignNewArr(peakY2, peakValleyWindows[selectedWell].minPeaks, setPeakY2);
    assignNewArr(valleyY1, peakValleyWindows[selectedWell].maxValleys, setValleyY1);
    assignNewArr(valleyY2, peakValleyWindows[selectedWell].maxValleys, setValleyY2);
  };

  const setBothLinesToNew = (newPeakY1, newPeakY2, newValleyY1, newValleyY2) => {
    assignNewArr(peakY1, newPeakY1, setPeakY1);
    assignNewArr(peakY2, newPeakY2, setPeakY2);
    assignNewArr(valleyY1, newValleyY1, setValleyY1);
    assignNewArr(valleyY2, newValleyY2, setValleyY2);
  };

  const isNewY = (yToCompare, originalYArr) => {
    return (
      yToCompare &&
      originalYArr.length !== 0 &&
      originalYArr[wellIdx] &&
      parseInt(yToCompare) !== parseInt(originalYArr[wellIdx])
    );
  };

  const filterFeature = (featureType, featureIndices, startTime, endTime, wellCoords, wellIndex) => {
    return featureIndices.filter((idx) => {
      // Can only filter if the data for this well has actually been loaded,
      // which is not guaranteed to be the case with the staggered loading of data for each well
      if (!wellCoords) return true;

      const [featureMarkerX, featureMarkerY] = wellCoords[idx];

      const featureThresholdY1 = featureType === "peak" ? peakY1 : valleyY1;
      const featureThresholdY2 = featureType === "peak" ? peakY2 : valleyY2;
      const featureThresholdY = calculateYLimit(
        featureThresholdY1[wellIndex],
        featureThresholdY2[wellIndex],
        featureMarkerX
      );

      const isFeatureWithinWindow = featureMarkerX >= startTime && featureMarkerX <= endTime;
      const isFeatureWithinThreshold =
        featureType === "peak" ? featureMarkerY >= featureThresholdY : featureMarkerY <= featureThresholdY;

      return isFeatureWithinThreshold && isFeatureWithinWindow;
    });
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
            selectedWellInfo={{ selectedWell, wellIdx: wellIdx }}
            timepointRange={timepointRange}
            waveformData={wellWaveformData}
            customAnalysisSettings={customAnalysisSettingsForWell}
            customAnalysisSettingsUpdaters={customAnalysisSettingsUpdaters}
            editableStartEndTimesHookItems={[editableStartEndTimes, setEditableStartEndTimes]}
            peakY1HookItems={[peakY1, setPeakY1]}
            peakY2HookItems={[peakY2, setPeakY2]}
            valleyY1HookItems={[valleyY1, setValleyY1]}
            valleyY2HookItems={[valleyY2, setValleyY2]}
            changelogActions={{
              save: saveChanges,
              undo: undoLastChange,
              reset: resetWellChanges,
              open: () => setOpenChangelog(true),
            }}
            filterFeature={filterFeature}
            checkDuplicates={checkDuplicates}
            calculateYLimit={calculateYLimit}
            assignNewArr={assignNewArr}
          />
        )}
      </GraphContainer>
      <ErrorLabel>{errorMessage}</ErrorLabel>
      <ParamContainer>
        <ParamLabel htmlFor="selectedPulse3dVersion">
          Pulse3d Version:
          <Tooltip
            title={
              <TooltipText>{"Specifies which version of the pulse3d analysis software to use."}</TooltipText>
            }
          >
            <InfoOutlinedIcon
              sx={{
                marginLeft: "5px",
                "&:hover": {
                  color: "var(--teal-green)",
                  cursor: "pointer",
                },
              }}
            />
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
              <InfoOutlinedIcon
                sx={{
                  marginLeft: "5px",
                  "&:hover": {
                    color: "var(--teal-green)",
                    cursor: "pointer",
                  },
                }}
              />
            </Tooltip>
          </ParamLabel>
          <FormInput
            name="nameOverride"
            placeholder={""}
            value={nameOverride}
            onChangeFn={(e) => {
              setNameOverride(e.target.value);
            }}
          />
        </ParamContainer>
      )}
      <ButtonContainer>
        <ButtonWidget
          width="150px"
          height="50px"
          position="relative"
          borderRadius="3px"
          left="-70px"
          label="Cancel"
          clickFn={() => setOpenInteractiveAnalysis(false)}
        />
        <ButtonWidget
          width="150px"
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
        open={duplicateModalOpen}
        buttons={constantModalLabels.duplicate.buttons}
        closeModal={handleDuplicatesModalClose}
        header={constantModalLabels.duplicate.header}
        labels={constantModalLabels.duplicate.messages}
      />
      <ModalWidget
        open={openChangelog}
        buttons={["Close"]}
        width={900}
        closeModal={() => setOpenChangelog(false)}
        header={`Changelog for ${selectedWell}`}
        labels={
          changelog[selectedWell] && changelog[selectedWell].length > 0
            ? changelog[selectedWell].map(({ message }) => message)
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
