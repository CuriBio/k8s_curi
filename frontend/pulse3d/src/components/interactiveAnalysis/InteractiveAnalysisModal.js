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
import * as apache from "apache-arrow";
import { getPeaksValleysFromTable, getWaveformCoordsFromTable } from "@/utils/generic";

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

const getDefaultFeatures = () => {
  const features = {};
  for (const well of wellNames) {
    features[well] = [null, null];
  }
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

  const [wellIdx, setWellIdx] = useState(0); // TODO use well name everywhere instead
  const [selectedWell, setSelectedWell] = useState("A1");

  const [originalData, setOriginalData] = useState({}); // original waveform data from GET request, unedited
  const [baseData, setBaseData] = useState({}); // same originalData but can have dups removed
  const [xRange, setXRange] = useState({
    // This is a copy of the max/min timepoints of the data. Windowed analysis start/stop times are set in editableStartEndTimes
    min: null,
    max: null,
  });

  const [dataToGraph, setDataToGraph] = useState([]); // well-specfic coordinates to graph
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

  useEffect(() => {
    const compatibleVersions = pulse3dVersions.filter((v) => semverGte(v, "0.28.3"));
    setFilteredVersions([...compatibleVersions]);

    if (usageQuota && usageQuota.limits && numberOfJobsInUpload >= 2 && usageQuota.limits.jobs !== -1) {
      setCreditUsageAlert(true);
    }
  }, []);

  useEffect(() => {
    if (removeDupsChecked) {
      const currentPeaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
      // remove duplicate peaks and valleys per well
      for (const well in currentPeaksValleysCopy) {
        currentPeaksValleysCopy[well] = removeWellSpecificDuplicates(well);
      }
      setBaseData(currentPeaksValleysCopy);
    } else {
      // if unchecked, revert back to previous peaks and valleys
      setBaseData(originalData.peaksValleys);
    }
  }, [removeDupsChecked]);

  useEffect(() => {
    // This is just to update the editable peaks and valleys correctly after the useEffect above
    setEditablePeaksValleys(baseData);
  }, [baseData]);

  useEffect(() => {
    // updates changelog when peaks/valleys and start/end times change
    if (undoing) {
      setUndoing(false);
    } else {
      updateChangelog();
    }
  }, [editableStartEndTimes, editablePeaksValleys, peakValleyWindows, peakY1, peakY2, valleyY1, valleyY2]);

  useEffect(() => {
    if (dataToGraph.length > 0) {
      setIsLoading(false);
    }

    if (
      // check if these are empty
      [peakY1, peakY2, valleyY1, valleyY2].filter((arr) => arr[wellIdx] == null).length > 0 &&
      peakValleyWindows[selectedWell]
    ) {
      setBothLinesToDefault();
    }
  }, [dataToGraph, editablePeaksValleys]);

  const getWaveformData = async () => {
    try {
      const wasmModule = await import("parquet-wasm/esm/arrow1.js");
      await wasmModule.default();

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/waveform-data?upload_id=${selectedJob.uploadId}&job_id=${selectedJob.jobId}`
      );

      if (response.status !== 200) throw Error();

      const buffer = await response.json();

      const peaksValleysParquet = wasmModule.readParquet(Object.values(buffer.peaksValleys));
      const peaksValleysTable = apache.tableFromIPC(peaksValleysParquet);
      const peaksValleys = await getPeaksValleysFromTable(peaksValleysTable);

      const timeForceParquet = wasmModule.readParquet(Object.values(buffer.timeForceData));
      const timeForceTable = apache.tableFromIPC(timeForceParquet);
      const coordinates = await getWaveformCoordsFromTable(timeForceTable, buffer.normalizeYAxis);

      originalData = { peaksValleys, coordinates };
      setOriginalData(originalData);
      setEditablePeaksValleys(peaksValleys);

      const { start_time, end_time } = selectedJob.analysisParams;

      xRange = {
        min: start_time || Math.min(...coordinates["A1"].map((coords) => coords[0])),
        max: end_time || Math.max(...coordinates["A1"].map((coords) => coords[0])),
      };
      setXRange(xRange);

      setEditableStartEndTimes({
        startTime: xRange.min,
        endTime: xRange.max,
      });

      // won't be present for older recordings or if no replacement was ever given
      if ("nameOverride" in selectedJob) setNameOverride(selectedJob.nameOverride);
      // setup initial peak valley thresholds
      setInitialPeakValleyWindows();
      // this function actually renders new graph data to the page
      setDataToGraph([...coordinates["A1"]]);

      if (!semverGte(selectedJob.analysisParams.pulse3d_version, "0.28.3")) {
        setModalLabels(constantModalLabels.oldPulse3dVersion);
        setModalOpen("pulse3dWarning");
      }
    } catch (e) {
      console.log("ERROR getting waveform data", e);
      // open error modal and kick users back to /uploads page if random  error
      setModalLabels(constantModalLabels.error);
      setModalOpen("status");
    }
  };

  const checkDuplicates = (
    well = selectedWell,
    peaks,
    valleys,
    peakThresholdY1 = peakY1[wellIdx],
    peakThresholdY2 = peakY2[wellIdx],
    valleyThresholdY1 = valleyY1[wellIdx],
    valleyThresholdY2 = valleyY2[wellIdx],
    start = editableStartEndTimes.startTime,
    end = editableStartEndTimes.endTime
  ) => {
    const wellIndex = twentyFourPlateDefinition.getWellIndexFromName(well);
    // filter
    const wellCoords = originalData.coordinates[well];
    const peakIndices = filterFeature(
      "peak",
      peaks,
      start,
      end,
      wellCoords,
      wellIndex,
      peakThresholdY1,
      peakThresholdY2
    );

    const valleyIndices = filterFeature(
      "valley",
      valleys,
      start,
      end,
      wellCoords,
      wellIndex,
      valleyThresholdY1,
      valleyThresholdY2
    );

    // create list with all features in order
    const features = [];
    for (const idx of peakIndices) {
      features.push({ type: "peak", idx });
    }
    for (const idx of valleyIndices) {
      features.push({ type: "valley", idx });
    }
    features.sort((a, b) => a.idx - b.idx);

    const duplicates = { peak: [], valley: [] };

    for (let i = 0; i < features.length; i++) {
      const [curr, next] = features.slice(i, i + 2);
      if (curr && next && curr.type === next.type) {
        duplicates[curr.type].push(curr.idx);
      }
    }

    return duplicates;
  };

  const setInitialPeakValleyWindows = () => {
    const windows = {};

    for (const well of wellNames) {
      windows[well] = {
        minPeaks: findLowestPeak(well),
        maxValleys: findHighestValley(well),
      };
    }

    setPeakValleyWindows(windows);
  };

  const findLowestPeak = (well) => {
    const { coordinates, peaksValleys } = originalData;
    const { max, min } = xRange;

    const wellSpecificPeaks = peaksValleys[well][0];
    const wellSpecificCoords = coordinates[well];
    // consider when no peaks or valleys were found in a well
    if (wellSpecificCoords && wellSpecificPeaks.length > 0) {
      const windowedPeaks = wellSpecificPeaks.filter((peak) => {
        // only use peaks inside windowed analysis times
        const timeOfPeak = wellSpecificCoords[peak][0];
        const isLessThanEndTime = !max || timeOfPeak <= max;
        const isGreaterThanStartTime = !min || timeOfPeak >= min;
        // filter for peaks inside windowed time
        return isGreaterThanStartTime && isLessThanEndTime;
      });

      // makes sure the initial valley to compare is within window
      let lowest = windowedPeaks[0];

      wellSpecificPeaks.map((peak) => {
        const yCoord = wellSpecificCoords[peak][1];
        const peakToCompare = wellSpecificCoords[lowest][1];
        // filter for peaks inside windowed time
        if (yCoord < peakToCompare) lowest = peak;
      });

      // return  y coordinate of lowest peak
      return wellSpecificCoords[lowest][1];
    }
  };

  const findHighestValley = (well) => {
    const { coordinates, peaksValleys } = originalData;
    const { max, min } = xRange;

    const wellSpecificValleys = peaksValleys[well][1];
    const wellSpecificCoords = coordinates[well];

    // consider when no peaks or valleys were found in a well
    if (wellSpecificCoords && wellSpecificValleys.length > 0) {
      const windowedValleys = wellSpecificValleys.filter((valley) => {
        // only use valleys inside windowed analysis times
        const timeOfValley = wellSpecificCoords[valley][0];
        const isLessThanEndTime = !max || timeOfValley <= max;
        const isGreaterThanStartTime = !min || timeOfValley >= min;
        return isLessThanEndTime && isGreaterThanStartTime;
      });

      // makes sure the initial valley to compare is within window
      let highest = windowedValleys[0];

      windowedValleys.map((valley) => {
        const yCoord = wellSpecificCoords[valley][1];
        const valleyToCompare = wellSpecificCoords[highest][1];

        if (yCoord > valleyToCompare) highest = valley;
      });

      // return  y coordinate of highest valley
      return wellSpecificCoords[highest][1];
    }
  };

  const resetStartEndTimes = () => {
    setEditableStartEndTimes({
      startTime: xRange.min,
      endTime: xRange.max,
    });
  };

  const loadExistingData = () => {
    // this happens very fast so not storing to react state the first call, see line 162 (? different line now)
    const jsonData = sessionStorage.getItem(selectedJob.jobId);
    const existingData = JSON.parse(jsonData);

    // not destructuring existingData to prevent confusion with local state names
    setOriginalData(existingData.originalData);
    setEditablePeaksValleys(existingData.editablePeaksValleys);
    setChangelog(existingData.changelog);
    setEditableStartEndTimes({
      startTime: existingData.editableStartEndTimes.startTime,
      endTime: existingData.editableStartEndTimes.endTime,
    });
    setPeakValleyWindows(existingData.peakValleyWindows);
    setPeakY1(existingData.peakY1);
    setPeakY2(existingData.peakY2);
    setValleyY1(existingData.valleyY1);
    setValleyY2(existingData.valleyY2);
  };

  const handleWellSelection = async (idx) => {
    const wellName = wellNames[idx];
    if (wellName !== selectedWell) {
      setSelectedWell(wellName);
      setWellIdx(idx);

      const coordinates = originalData.coordinates[wellName];
      setDataToGraph([...coordinates]);
    }
  };

  const resetWellChanges = () => {
    // reset peaks and valleys for current well
    const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
    const changelogCopy = JSON.parse(JSON.stringify(changelog));
    const pvWindowCopy = JSON.parse(JSON.stringify(peakValleyWindows));
    const baseDataCopy = JSON.parse(JSON.stringify(baseData[selectedWell]));

    if (changelogCopy[selectedWell] && changelogCopy[selectedWell].length > 0) {
      peaksValleysCopy[selectedWell] = baseDataCopy;

      changelogCopy[selectedWell] = [];

      pvWindowCopy[selectedWell] = {
        minPeaks: findLowestPeak(selectedWell),
        maxValleys: findHighestValley(selectedWell),
      };

      // reset state
      resetStartEndTimes();
      setEditablePeaksValleys(peaksValleysCopy);
      setChangelog(changelogCopy);
      setPeakValleyWindows(pvWindowCopy);
      setBothLinesToDefault();
      setDisableRemoveDupsCheckbox(isRemoveDuplicatesDisabled(changelogCopy));
    }
  };

  const postNewJob = async () => {
    try {
      setUploadInProgress(true);

      const filteredPeaksValleys = await filterPeaksValleys();

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

  const handleModalClose = async (i) => {
    if (modalOpen !== "pulse3dWarning") {
      if (modalOpen === "status") setOpenInteractiveAnalysis(false);
      else if (i === 0) {
        await getWaveformData();
      } else {
        loadExistingData();
      }
      sessionStorage.removeItem(selectedJob.jobId);
    }

    setModalOpen(false);
  };

  const filterPeaksValleys = async () => {
    const filtered = {};
    const { startTime, endTime } = JSON.parse(JSON.stringify(editableStartEndTimes));

    for (const well in editablePeaksValleys) {
      const wellIndex = twentyFourPlateDefinition.getWellIndexFromName(well);
      const wellCoords = originalData.coordinates[well];

      let [peakIndices, valleyIndices] = editablePeaksValleys[well];

      peakIndices = filterFeature("peak", peakIndices, startTime, endTime, wellCoords, wellIndex);
      valleyIndices = filterFeature("valley", valleyIndices, startTime, endTime, wellCoords, wellIndex);

      filtered[well] = [peakIndices, valleyIndices];
    }

    return filtered;
  };

  const saveChanges = () => {
    // TODO handle if for some reason this is full and returns error
    sessionStorage.setItem(
      selectedJob.jobId,
      JSON.stringify({
        editableStartEndTimes,
        editablePeaksValleys,
        originalData,
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
    } else if (baseData && baseData[selectedWell]) {
      // If are no changes detected then add default values to first index of changelog
      const baseWellData = baseData[selectedWell];
      const maxValleyY = findHighestValley(selectedWell);
      const minPeakY = findLowestPeak(selectedWell);

      const defaultChangelog = {
        peaks: baseWellData[0],
        valleys: baseWellData[1],
        startTime: xRange.min,
        endTime: xRange.max,
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

  const compareFeatures = (oldFeatures, newFeatures) => {
    for (const idx of newFeatures) {
      if (!oldFeatures.includes(idx)) {
        return idx;
      }
    }
    return -1;
  };

  const getChangelogMessage = ({
    peaks: peaksToCompare,
    valleys: valleysToCompare,
    startTime: startToCompare,
    endTime: endToCompare,
    valleyYOne: valleyY1ToCompare,
    valleyYTwo: valleyY2ToCompare,
    peakYOne: peakY1ToCompare,
    peakYTwo: peakY2ToCompare,
  }) => {
    const featuresForWell = editablePeaksValleys[selectedWell];

    let changelogMessage;
    const peaksMoved =
        JSON.stringify(peaksToCompare) !== JSON.stringify(featuresForWell[0]) &&
        peaksToCompare.length === featuresForWell[0].length,
      peakAdded = peaksToCompare.length < featuresForWell[0].length,
      peakDeleted = peaksToCompare.length > featuresForWell[0].length,
      valleysMoved =
        JSON.stringify(valleysToCompare) !== JSON.stringify(featuresForWell[1]) &&
        valleysToCompare.length === featuresForWell[1].length,
      valleyAdded = valleysToCompare.length < featuresForWell[1].length,
      valleyDeleted = valleysToCompare.length > featuresForWell[1].length,
      startTimeDiff =
        startToCompare !== editableStartEndTimes.startTime &&
        editableStartEndTimes.startTime !== null &&
        startToCompare !== null,
      endTimeDiff =
        endToCompare !== editableStartEndTimes.endTime &&
        editableStartEndTimes.endTime !== null &&
        endToCompare !== null,
      windowedTimeDiff = startTimeDiff && endTimeDiff,
      isNewValleyY1 = isNewY(valleyY1ToCompare, valleyY1),
      isNewValleyY2 = isNewY(valleyY2ToCompare, valleyY2),
      isNewPeakY1 = isNewY(peakY1ToCompare, peakY1),
      isNewPeakY2 = isNewY(peakY2ToCompare, peakY2);

    if (peaksMoved) {
      const diffIdx = peaksToCompare.findIndex((peakIdx, i) => peakIdx !== featuresForWell[0][i]),
        oldPeakX = dataToGraph[peaksToCompare[diffIdx]][0],
        oldPeakY = dataToGraph[peaksToCompare[diffIdx]][1],
        newPeakX = dataToGraph[featuresForWell[0][diffIdx]][0],
        newPeakY = dataToGraph[featuresForWell[0][diffIdx]][1];

      changelogMessage = `Peak at [ ${oldPeakX.toFixed(2)}, ${oldPeakY.toFixed(
        2
      )} ] was moved to [ ${newPeakX.toFixed(2)}, ${newPeakY.toFixed(2)} ].`;
    } else if (peakAdded) {
      const newIdx = compareFeatures(peaksToCompare, featuresForWell[0]);
      if (newIdx >= 0) {
        const coordinates = dataToGraph[newIdx];
        changelogMessage = `Peak was added at [ ${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(2)} ]`;
      }
    } else if (peakDeleted) {
      const newIdx = compareFeatures(featuresForWell[0], peaksToCompare);
      if (newIdx >= 0) {
        const coordinates = dataToGraph[newIdx];
        changelogMessage = `Peak at [ ${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(
          2
        )} ] was removed.`;
      }
    } else if (valleysMoved) {
      const diffIdx = valleysToCompare.findIndex((valleyIdx, i) => valleyIdx !== featuresForWell[1][i]),
        oldValleyX = dataToGraph[valleysToCompare[diffIdx]][0],
        oldValleyY = dataToGraph[valleysToCompare[diffIdx]][1],
        newValleyX = dataToGraph[featuresForWell[1][diffIdx]][0],
        newValleyY = dataToGraph[featuresForWell[1][diffIdx]][1];

      changelogMessage = `Valley at [ ${oldValleyX.toFixed(2)}, ${oldValleyY.toFixed(
        2
      )} ] was moved to [ ${newValleyX.toFixed(2)}, ${newValleyY.toFixed(2)} ].`;
    } else if (valleyAdded) {
      const newIdx = compareFeatures(valleysToCompare, featuresForWell[1]);
      if (newIdx >= 0) {
        const coordinates = dataToGraph[newIdx];
        changelogMessage = `Valley was added at [ ${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(
          2
        )} ]`;
      }
    } else if (valleyDeleted) {
      const newIdx = compareFeatures(featuresForWell[1], valleysToCompare);
      if (newIdx >= 0) {
        const coordinates = dataToGraph[newIdx];
        changelogMessage = `Valley at [ ${coordinates[0].toFixed(2)}, ${coordinates[1].toFixed(
          2
        )} ] was removed.`;
      }
    } else if (windowedTimeDiff) {
      changelogMessage = `Start time was changed from ${startToCompare} to ${editableStartEndTimes.startTime} and end time was changed from ${endToCompare} to ${editableStartEndTimes.endTime}.`;
    } else if (startTimeDiff) {
      changelogMessage = `Start time was changed from ${startToCompare} to ${editableStartEndTimes.startTime}.`;
    } else if (endTimeDiff) {
      changelogMessage = `End time was changed from ${endToCompare} to ${editableStartEndTimes.endTime}.`;
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

  const deletePeakValley = (peakValley, idx) => {
    const typeIdx = ["peak", "valley"].indexOf(peakValley);
    const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
    const targetIdx = peaksValleysCopy[selectedWell][typeIdx].indexOf(idx);

    if (targetIdx > -1) {
      // remove desired marker
      peaksValleysCopy[selectedWell][typeIdx].splice(targetIdx, 1);
      setEditablePeaksValleys({ ...peaksValleysCopy });
    }
  };

  const addPeakValley = (peakValley, targetTime) => {
    const typeIdx = ["peak", "valley"].indexOf(peakValley);
    const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
    const indexToAdd = dataToGraph.findIndex(
      (coord) => Number(coord[0].toFixed(2)) === Number(targetTime.toFixed(2))
    );

    peaksValleysCopy[selectedWell][typeIdx].push(indexToAdd);
    setEditablePeaksValleys({ ...peaksValleysCopy });
  };

  const addToChangelog = (message) => {
    if (!changelog[selectedWell]) changelog[selectedWell] = [];
    // if you don't deep copy state, later changes will affect change log entries here
    const { startTime, endTime } = JSON.parse(JSON.stringify(editableStartEndTimes));
    const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
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

    setDisableRemoveDupsCheckbox(isRemoveDuplicatesDisabled(changelog));
    setChangelog(changelog);
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
    Object.keys(editablePeaksValleys).map((well) => {
      const wellIndex = twentyFourPlateDefinition.getWellIndexFromName(well);
      const { peak, valley } = checkDuplicates(
        well,
        editablePeaksValleys[well][0],
        editablePeaksValleys[well][1],
        peakY1[wellIndex],
        peakY2[wellIndex],
        valleyY1[wellIndex],
        valleyY2[wellIndex]
      );
      // if any duplicates are present, push well into storage array to add to modal letting user know which wells are affected
      if (peak.length > 0 || valley.length > 0) wellsWithDups.push(well);
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
    if (changelog[selectedWell] && changelog[selectedWell].length > 0) {
      // undoing state tells the updateChangelog useEffect to not ignore the change and not as a new change
      setUndoing(true);
      // make copies so you control when state is updated
      const changesCopy = JSON.parse(JSON.stringify(changelog[selectedWell]));
      const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
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

        // update values to state to rerender graph
        setEditableStartEndTimes(newWindowTimes);
        setEditablePeaksValleys(peaksValleysCopy);
        setPeakValleyWindows(pvWindowCopy);
        setDisableRemoveDupsCheckbox(isRemoveDuplicatesDisabled(changelog));

        // save new changelog state
        changelog[selectedWell] = changesCopy;
        setChangelog(changelog);
      } else {
        // if undoing the very first change, revert back to original state
        resetWellChanges();
      }
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

  const filterFeature = (
    featureType,
    featureIndices,
    startTime,
    endTime,
    wellCoords,
    wellIndex = wellIdx,
    featureThresholdY1,
    featureThresholdY2
  ) => {
    const featureThresholdsY1 = {
      peak: featureThresholdY1 || peakY1[wellIndex],
      valley: featureThresholdY1 || valleyY1[wellIndex],
    };

    const featureThresholdsY2 = {
      peak: featureThresholdY2 || peakY2[wellIndex],
      valley: featureThresholdY2 || valleyY2[wellIndex],
    };

    return featureIndices.filter((idx) => {
      // Can only filter if the data for this well has actually been loaded,
      // which is not guaranteed to be the case with the staggered loading of data for each well
      if (!wellCoords) return true;

      const [featureMarkerX, featureMarkerY] = wellCoords[idx];

      const featureThresholdY = calculateYLimit(
        featureThresholdsY1[featureType],
        featureThresholdsY2[featureType],
        featureMarkerX
      );

      const isFeatureWithinWindow = featureMarkerX >= startTime && featureMarkerX <= endTime;
      const isFeatureWithinThreshold =
        featureType === "peak" ? featureMarkerY >= featureThresholdY : featureMarkerY <= featureThresholdY;

      return isFeatureWithinThreshold && isFeatureWithinWindow;
    });
  };

  const removeDuplicateFeatures = (duplicates, sortedFeatures) => {
    for (const feature of duplicates) {
      const idxToCheck = sortedFeatures.indexOf(feature);
      sortedFeatures.splice(idxToCheck, 1);
    }
    return sortedFeatures;
  };

  const removeWellSpecificDuplicates = (well) => {
    const [ogPeaks, ogValleys] = JSON.parse(JSON.stringify(originalData.peaksValleys[well]));
    const sortedPeaks = ogPeaks.sort((a, b) => a - b);
    const sortedValleys = ogValleys.sort((a, b) => a - b);

    const { minPeaks, maxValleys } = {
      minPeaks: findLowestPeak(well),
      maxValleys: findHighestValley(well),
    };

    const duplicateFeatures = checkDuplicates(
      well,
      ogPeaks,
      ogValleys,
      minPeaks,
      minPeaks,
      maxValleys,
      maxValleys,
      xRange.min,
      xRange.max
    );

    const { peak, valley } = JSON.parse(JSON.stringify(duplicateFeatures));

    const sortedDupPeaks = peak.sort((a, b) => a - b);
    const sortedDupValleys = valley.sort((a, b) => a - b);

    return [
      removeDuplicateFeatures(sortedDupPeaks, sortedPeaks),
      removeDuplicateFeatures(sortedDupValleys, sortedValleys),
    ];
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
  useMemo(async () => {
    const data = sessionStorage.getItem(selectedJob.jobId); // returns null if key doesn't exist in storage
    if (data) {
      // if data is found in sessionStorage then do ?
      setModalLabels(constantModalLabels.dataFound);
      setModalOpen("dataFound");
    } else {
      // if no data stored, then need to retrieve from server
      await getWaveformData();
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
            selectedWellInfo={{ selectedWell, wellIdx }}
            xRange={xRange}
            dataToGraph={dataToGraph}
            editableStartEndTimesHookItems={[editableStartEndTimes, setEditableStartEndTimes]}
            editablePeaksValleysHookItems={[editablePeaksValleys, setEditablePeaksValleys]}
            peakValleyWindows={peakValleyWindows}
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
            deletePeakValley={deletePeakValley}
            addPeakValley={addPeakValley}
            filterFeature={filterFeature}
            checkDuplicates={checkDuplicates}
            calculateYLimit={calculateYLimit}
            assignNewArr={assignNewArr}
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
