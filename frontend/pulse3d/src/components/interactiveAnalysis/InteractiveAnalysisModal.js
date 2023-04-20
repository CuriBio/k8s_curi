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
      "Please re-analyze this recording using a Pulse3D version greater than 0.28.2 or continue.",
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

export default function InteractiveWaveformModal({
  selectedJob,
  setOpenInteractiveAnalysis,
  numberOfJobsInUpload,
}) {
  const { usageQuota } = useContext(AuthContext);
  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);

  const [selectedWell, setSelectedWell] = useState("A1");
  const [uploadInProgress, setUploadInProgress] = useState(false); // determines state of interactive analysis upload
  const [originalData, setOriginalData] = useState({}); // original waveform data from GET request, unedited
  const [dataToGraph, setDataToGraph] = useState([]); // well-specfic coordinates to graph
  const [isLoading, setIsLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalLabels, setModalLabels] = useState(constantModalLabels.success);
  const [editablePeaksValleys, setEditablePeaksValleys] = useState(); // user edited peaks/valleys as changes are made, should get stored in localStorage
  const [errorMessage, setErrorMessage] = useState();
  const [markers, setMarkers] = useState([]);
  const [pulse3dVersionIdx, setPulse3dVersionIdx] = useState(0);
  const [filteredVersions, setFilteredVersions] = useState([]);
  const [changelog, setChangelog] = useState({});
  const [openChangelog, setOpenChangelog] = useState(false);
  const [undoing, setUndoing] = useState(false);
  const [peakValleyWindows, setPeakValleyWindows] = useState({});
  const [duplicateModalOpen, setDuplicateModalOpen] = useState(false);
  const [creditUsageAlert, setCreditUsageAlert] = useState(false);
  const [deprecationNotice, setDeprecationNotice] = useState(false);
  const [pulse3dVersionEOLDate, setPulse3dVersionEOLDate] = useState("");
  const [nameOverride, setNameOverride] = useState();
  const [xRange, setXRange] = useState({
    min: null,
    max: null,
  });
  const [editableStartEndTimes, setEditableStartEndTimes] = useState({
    startTime: null,
    endTime: null,
  });
  //state for peaks
  const [peakY1, setPeakY1] = useState([]);
  const [peakY2, setPeakY2] = useState([]);
  //state for valleys
  const [valleyY1, setValleyY1] = useState([]);
  const [valleyY2, setValleyY2] = useState([]);

  useEffect(() => {
    // only available for versions greater than 0.25.2
    const compatibleVersions = pulse3dVersions.filter((v) => semverGte(v, "0.25.2"));
    setFilteredVersions([...compatibleVersions]);
    if (usageQuota && usageQuota.limits && numberOfJobsInUpload >= 2 && usageQuota.limits.jobs !== -1) {
      setCreditUsageAlert(true);
    }
  }, []);

  useEffect(() => {
    // updates changelog when peaks/valleys and start/end times change
    if (!undoing) updateChangelog();
    else setUndoing(false);
  }, [markers, editableStartEndTimes, peakValleyWindows, peakY1, peakY2, valleyY1, valleyY2]);

  useEffect(() => {
    if (dataToGraph.length > 0) {
      setMarkers([...editablePeaksValleys[selectedWell]]);
      setIsLoading(false);
    }
  }, [dataToGraph, editablePeaksValleys]);

  const getWaveformData = async (peaks_valleys_needed, well) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/waveform-data?upload_id=${selectedJob.uploadId}&job_id=${selectedJob.jobId}&peaks_valleys=${peaks_valleys_needed}&well_name=${well}`
      );

      if (response.status === 200) {
        const res = await response.json();
        if (!res.error) {
          if (!("coordinates" in originalData)) {
            originalData = {
              peaks_valleys: res.peaks_valleys,
              coordinates: {},
            };
          }

          const { coordinates, peaks_valleys } = res;
          // original data is set and never changed to hold original state in case of reset
          originalData.coordinates[well] = coordinates;
          setOriginalData(originalData);
          if (peaks_valleys_needed) {
            const { start_time, end_time } = selectedJob.analysisParams;

            setEditablePeaksValleys(peaks_valleys);
            setXRange({
              min: start_time ? start_time : Math.min(...coordinates.map((coords) => coords[0])),
              max: end_time ? end_time : Math.max(...coordinates.map((coords) => coords[0])),
            });

            // won't be present for older recordings or if no replacement was ever given
            if ("nameOverride" in selectedJob) setNameOverride(selectedJob.nameOverride);
          }

          setInitialPeakValleyWindows(well);
          // this function actually renders new graph data to the page
          setDataToGraph([...coordinates]);

          if (!semverGte(selectedJob.analysisParams.pulse3d_version, "0.28.2")) {
            setModalLabels(constantModalLabels.oldPulse3dVersion);
            setModalOpen("pulse3dWarning");
          }
        } else {
          throw Error();
        }
      } else {
        throw Error();
      }
    } catch (e) {
      console.log("ERROR getting waveform data: ", e);
      // open error modal and kick users back to /uploads page if random  error
      setModalLabels(constantModalLabels.error);
      setModalOpen("status");
    }
  };

  const checkDuplicates = (well) => {
    const wellToUse = well ? well : selectedWell;

    let peaksList = editablePeaksValleys[wellToUse][0].sort((a, b) => a - b);
    let valleysList = editablePeaksValleys[wellToUse][1].sort((a, b) => a - b);

    // if data for a well was never fetched, assume no filtering required because the user would not have moved the peaks and valley lines. Just checked duplicates against original peaks and valleys
    if (wellToUse in originalData.coordinates) {
      const dataToCompare = originalData.coordinates[wellToUse];

      peaksList = peaksList.filter((peak) => dataToCompare[peak][1] >= peakValleyWindows[wellToUse].minPeaks);
      valleysList = valleysList.filter(
        (valley) => dataToCompare[valley][1] <= peakValleyWindows[wellToUse].maxValleys
      );
    }

    let peakIndex = 0;
    let valleyIndex = 0;
    const time = [];
    const type = [];

    // create two arrays one for type of data and one for the time of data
    while (peakIndex < peaksList.length && valleyIndex < valleysList.length) {
      if (peaksList[peakIndex] < valleysList[valleyIndex]) {
        time.push(peaksList[peakIndex]);
        type.push("peak");
        peakIndex++;
      } else if (valleysList[valleyIndex] < peaksList[peakIndex]) {
        time.push(valleysList[valleyIndex]);
        type.push("valley");
        valleyIndex++;
      } else {
        //if equal
        time.push(peaksList[peakIndex]);
        type.push("peak");
        peakIndex++;
        time.push(valleysList[valleyIndex]);
        type.push("valley");
        valleyIndex++;
      }
    }
    while (peakIndex !== peaksList.length) {
      time.push(peaksList[peakIndex]);
      type.push("peak");
      peakIndex++;
    }
    while (valleyIndex !== valleysList.length) {
      time.push(valleysList[valleyIndex]);
      type.push("valley");
      valleyIndex++;
    }
    //create a final map containing data point time as key
    //and bool representing if marker is a duplicate as value
    const duplicatesMap = {};
    for (let i = 1; i < time.length; i++) {
      duplicatesMap[time[i]] = type[i] === type[i + 1] || type[i] === type[i - 1];
    }

    return duplicatesMap;
  };

  const getNewData = async () => {
    const { start_time, end_time } = selectedJob.analysisParams;

    await getWaveformData(true, "A1");

    setEditableStartEndTimes({
      startTime: start_time,
      endTime: end_time,
    });
  };

  const checkForExistingData = () => {
    const data = sessionStorage.getItem(selectedJob.jobId);
    // returns null if key doesn't exist in storage
    if (data) {
      setModalLabels(constantModalLabels.dataFound);
      setModalOpen("dataFound");
    } else {
      getNewData();
    }
  };

  // Luci (12-14-2022) this component gets mounted twice and we don't want this expensive function to request waveform data to be called twice. This ensures it is only called once per job selection
  useMemo(checkForExistingData, [selectedJob]);

  const setInitialPeakValleyWindows = (well) => {
    const pvCopy = JSON.parse(JSON.stringify(peakValleyWindows));

    pvCopy[well] = {
      minPeaks: findLowestPeak(well),
      maxValleys: findHighestValley(well),
    };

    setPeakValleyWindows({
      ...pvCopy,
    });
  };

  const findLowestPeak = (well) => {
    const { coordinates, peaks_valleys } = originalData;
    const { startTime, endTime } = editableStartEndTimes;
    // arbitrarily set to first peak
    const wellSpecificPeaks = peaks_valleys[well][0];
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
    const { coordinates, peaks_valleys } = originalData;
    const { startTime, endTime } = editableStartEndTimes;
    // arbitrarily set to first valley
    const wellSpecificValleys = peaks_valleys[well][1];
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

  const loadExistingData = () => {
    // this happens very fast so not storing to react state the first call, see line 162
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
    getWaveformData(true, selectedWell);
  };

  const handleWellSelection = async (idx) => {
    if (wellNames[idx] !== selectedWell) {
      setSelectedWell(wellNames[idx]);
      if (!(wellNames[idx] in originalData.coordinates)) {
        setIsLoading(true);
        getWaveformData(false, wellNames[idx]);
      } else {
        const coordinates = originalData.coordinates[wellNames[idx]];
        setDataToGraph([...coordinates]);
      }
    }
  };

  const resetWellChanges = () => {
    // reset peaks and valleys for current well
    const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
    const changelogCopy = JSON.parse(JSON.stringify(changelog));
    const pvWindowCopy = JSON.parse(JSON.stringify(peakValleyWindows));
    peaksValleysCopy[selectedWell] = originalData.peaks_valleys[selectedWell];
    changelogCopy[selectedWell] = [];
    pvWindowCopy[selectedWell] = {
      minPeaks: findLowestPeak(selectedWell),
      maxValleys: findHighestValley(selectedWell),
    };
    // reset state
    setEditablePeaksValleys(peaksValleysCopy);
    setChangelog(changelogCopy);
    setPeakValleyWindows(pvWindowCopy);
    setBothLinesToDefault();
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

  const handleModalClose = (i) => {
    if (modalOpen !== "pulse3dWarning") {
      if (modalOpen === "status") setOpenInteractiveAnalysis(false);
      else if (i === 0) getNewData();
      else {
        loadExistingData();
      }
      sessionStorage.removeItem(selectedJob.jobId);
    }

    setModalOpen(false);
  };

  const filterPeaksValleys = async () => {
    const filtered = {};
    for (const well of Object.keys(editablePeaksValleys)) {
      let wellPeaks = editablePeaksValleys[well][0];
      let wellValleys = editablePeaksValleys[well][1];

      // only filter if well data has been fetched, otherwise assume no filtering required because user would not have been able to have moved min peak and max valley lines
      if (well in originalData.coordinates) {
        const wellCoords = originalData.coordinates[well];
        wellPeaks = wellPeaks.filter((peak) => {
          const isPeakWithinWindow = dataToGraph[peak][0] >= startTime && dataToGraph[peak][0] <= endTime;
          const peakMarkerY = wellCoords[peak][1];
          const wellIndex = twentyFourPlateDefinition.getIndexFromWellName(well);
          const peaksLimitY = calculateYLimit(peakY1[wellIndex], peakY2[wellIndex], wellCoords[peak][0]);
          return peakMarkerY >= peaksLimitY && isPeakWithinWindow;
        });
        wellValleys = wellValleys.filter((valley) => {
          const isValleyWithinWindow =
            dataToGraph[valley][0] >= startTime && dataToGraph[valley][0] <= endTime;
          const valleyMarkerY = wellCoords[valley][1];
          const wellIndex = twentyFourPlateDefinition.getIndexFromWellName(well);
          const valleyLimitY = calculateYLimit(
            valleyY1[wellIndex],
            valleyY2[wellIndex],
            wellCoords[valley][0]
          );
          return valleyMarkerY <= valleyLimitY && isValleyWithinWindow;
        });
      }
      filtered[well] = [wellPeaks, wellValleys];
    }
    return filtered;
  };

  const saveChanges = () => {
    // TODO handle is for some reason this is full and returns error
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
    // changelog will have length of 0 if a user Undo's until initial state
    if (changelog[selectedWell] && changelog[selectedWell].length > 0 && markers.length === 2) {
      //If Change log has changes
      const wellChanges = changelog[selectedWell];
      //Get snapshot of previus state
      const { peaks, valleys, startTime, endTime, pvWindow, valleyYOne, valleyYTwo, peakYOne, peakYTwo } =
        wellChanges[wellChanges.length - 1];
      changelogMessage = getChangelogMessage(
        peaks,
        valleys,
        startTime,
        endTime,
        pvWindow,
        valleyYOne,
        valleyYTwo,
        peakYOne,
        peakYTwo
      );
    } else if (markers.length === 2 && originalData.peaks_valleys[selectedWell]) {
      //If are no changes detected
      const ogWellData = originalData.peaks_valleys[selectedWell];
      changelogMessage = getChangelogMessage(
        ogWellData[0],
        ogWellData[1],
        xRange.min,
        xRange.max,
        {
          minPeaks: findLowestPeak(selectedWell),
          maxValleys: findHighestValley(selectedWell),
        },
        peakValleyWindows[selectedWell].maxValleys,
        peakValleyWindows[selectedWell].maxValleys,
        peakValleyWindows[selectedWell].minPeaks,
        peakValleyWindows[selectedWell].minPeaks
      );
    }

    if (changelogMessage !== undefined) {
      addToChangelog(changelogMessage);
    }
  };

  const getChangelogMessage = (
    peaksToCompare,
    valleysToCompare,
    startToCompare,
    endToCompare,
    pvWindow,
    valleyY1ToCompare,
    valleyY2ToCompare,
    peakY1ToCompare,
    peakY2ToCompare
  ) => {
    let changelogMessage;

    const peaksMoved =
        JSON.stringify(peaksToCompare) !== JSON.stringify(markers[0]) &&
        peaksToCompare.length === markers[0].length, // added and deleted peaks is handled somewhere else
      valleysMoved =
        JSON.stringify(valleysToCompare) !== JSON.stringify(markers[1]) &&
        valleysToCompare.length === markers[1].length, // added and deleted peaks is handled somewhere else,
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
      const diffIdx = peaksToCompare.findIndex((peakIdx, i) => peakIdx !== markers[0][i]),
        oldPeakX = dataToGraph[peaksToCompare[diffIdx]][0],
        oldPeakY = dataToGraph[peaksToCompare[diffIdx]][1],
        newPeakX = dataToGraph[markers[0][diffIdx]][0],
        newPeakY = dataToGraph[markers[0][diffIdx]][1];

      changelogMessage = `Peak at [ ${oldPeakX.toFixed(2)}, ${oldPeakY.toFixed(
        2
      )} ] was moved to [ ${newPeakX.toFixed(2)}, ${newPeakY.toFixed(2)} ].`;
    } else if (valleysMoved) {
      const diffIdx = valleysToCompare.findIndex((valleyIdx, i) => valleyIdx !== markers[0][i]),
        oldValleyX = dataToGraph[valleysToCompare[diffIdx]][0],
        oldValleyY = dataToGraph[valleysToCompare[diffIdx]][1],
        newValleyX = dataToGraph[markers[1][diffIdx]][0],
        newValleyY = dataToGraph[markers[1][diffIdx]][1];

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
      changelogMessage = `Valley Line moved ${
        valleyY1[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)] - valleyY1ToCompare
      }`;
    } else if (isNewPeakY1 && isNewPeakY2) {
      changelogMessage = `Peak Line moved ${
        peakY1[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)] - peakY1ToCompare
      }`;
    } else if (isNewValleyY1) {
      changelogMessage = `Valley Line Y1 switched to ${
        valleyY1[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)]
      }`;
    } else if (isNewValleyY2) {
      changelogMessage = `Valley Line Y2 switched to ${
        valleyY2[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)]
      }`;
    } else if (isNewPeakY1) {
      changelogMessage = `Peak Line Y1 switched to ${
        peakY1[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)]
      }`;
    } else if (isNewPeakY2) {
      changelogMessage = `Peak Line Y2 switched to ${
        peakY2[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)]
      }`;
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
      setMarkers([...peaksValleysCopy[selectedWell]]);

      const coordinates = dataToGraph[idx];
      const changelogMessage = `${typeIdx === 0 ? "Peak" : "Valley"} at [ ${coordinates[0].toFixed(
        2
      )}, ${coordinates[1].toFixed(2)} ] was removed.`;

      addToChangelog(changelogMessage);
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
    setMarkers([...peaksValleysCopy[selectedWell]]);

    const coordinates = dataToGraph[indexToAdd];
    const changelogMessage = `${typeIdx === 0 ? "Peak" : "Valley"} was added at [ ${coordinates[0].toFixed(
      2
    )}, ${coordinates[1].toFixed(2)} ]`;

    addToChangelog(changelogMessage);
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
      valleyYOne: valleyY1[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)],
      valleyYTwo: valleyY2[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)],
      peakYOne: peakY1[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)],
      peakYTwo: peakY2[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)],
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
    Object.keys(editablePeaksValleys).map((well) => {
      const duplicatesMap = checkDuplicates(well);
      // find any index marked as true, quantity doesn't matter
      const duplicatePresent = Object.keys(duplicatesMap).findIndex((idx) => duplicatesMap[idx]);
      // if present, push into storage array to add to modal letting user know which wells are affected
      if (duplicatePresent !== -1) wellsWithDups.push(well);
    });

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
      const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
      const pvWindowCopy = JSON.parse(JSON.stringify(peakValleyWindows));
      const newWindowTimes = {};
      // remove step with latest changes
      changesCopy.pop();

      if (changesCopy.length > 0) {
        // grab state from the step before the undo step to set as current state
        const { peaks, valleys, startTime, endTime, pvWindow, valleyYOne, valleyYTwo, peakYOne, peakYTwo } =
          changesCopy[changesCopy.length - 1];
        // set old peaks and valleys to well
        peaksValleysCopy[selectedWell] = [[...peaks], [...valleys]];
        pvWindowCopy[selectedWell] = pvWindow;
        newWindowTimes.startTime = startTime;
        newWindowTimes.endTime = endTime;
        setBothLinesToNew(peakYOne, peakYTwo, valleyYOne, valleyYTwo);
      } else {
        // if only one change was made, then you revert back to original state
        newWindowTimes.startTime = xRange.min;
        newWindowTimes.endTime = xRange.max;

        peaksValleysCopy[selectedWell] = originalData.peaks_valleys[selectedWell];
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
      setEditablePeaksValleys(peaksValleysCopy);
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
    const x1 = (editableStartEndTimes.endTime - editableStartEndTimes.startTime) / 100;
    const x2 =
      editableStartEndTimes.endTime - (editableStartEndTimes.endTime - editableStartEndTimes.startTime) / 100;
    const slope = (y2 - y1) / (x2 - x1);
    const yIntercept = y2 - slope * x2;
    return markerX * slope + yIntercept;
  };

  const setBothLinesToDefault = () => {
    const wellIndex = twentyFourPlateDefinition.getIndexFromWellName(selectedWell);
    setValleyLineDataToDefault(wellIndex);
    setPeakLineDataToDefault(wellIndex);
  };
  const setPeakLineDataToDefault = (wellIndex) => {
    let newArr = [...peakY1];
    newArr[wellIndex] = peakValleyWindows[selectedWell].minPeaks;
    setPeakY1(newArr);
    newArr = [...peakY2];
    newArr[wellIndex] = peakValleyWindows[selectedWell].minPeaks;
    setPeakY2(newArr);
  };

  const setValleyLineDataToDefault = (wellIndex) => {
    let newArr = [...valleyY1];
    newArr[wellIndex] = peakValleyWindows[selectedWell].maxValleys;
    setValleyY1(newArr);
    newArr = [...valleyY2];
    newArr[wellIndex] = peakValleyWindows[selectedWell].maxValleys;
    setValleyY2(newArr);
  };

  const setBothLinesToNew = (newPeakY1, newPeakY2, newValleyY1, newValleyY2) => {
    const wellIndex = twentyFourPlateDefinition.getIndexFromWellName(selectedWell);
    let arr = [...peakY1];
    arr[wellIndex] = newPeakY1;
    setPeakY1(arr);
    arr = [...peakY2];
    arr[wellIndex] = newPeakY2;
    setPeakY2(arr);
    arr = [...valleyY1];
    arr[wellIndex] = newValleyY1;
    setValleyY1(arr);
    arr = [...valleyY2];
    arr[wellIndex] = newValleyY2;
    setValleyY2(arr);
  };
  const isNewY = (yToCompare, originalYArr) => {
    return (
      yToCompare !== originalYArr[twentyFourPlateDefinition.getIndexFromWellName(selectedWell)] &&
      originalYArr &&
      originalYArr.length !== 0
    );
  };

  return (
    <Container>
      <HeaderContainer>Interactive Waveform Analysis</HeaderContainer>
      <WellDropdownContainer>
        <WellDropdownLabel>Select Well:</WellDropdownLabel>
        <DropDownWidget
          options={wellNames}
          handleSelection={handleWellSelection}
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
            dataToGraph={dataToGraph}
            initialPeaksValleys={markers}
            startTime={editableStartEndTimes.startTime}
            endTime={editableStartEndTimes.endTime}
            currentWell={selectedWell}
            setEditableStartEndTimes={setEditableStartEndTimes}
            setEditablePeaksValleys={setEditablePeaksValleys}
            editablePeaksValleys={editablePeaksValleys}
            xRange={xRange}
            resetWellChanges={resetWellChanges}
            saveChanges={saveChanges}
            deletePeakValley={deletePeakValley}
            addPeakValley={addPeakValley}
            openChangelog={() => setOpenChangelog(true)}
            undoLastChange={undoLastChange}
            peakValleyWindows={peakValleyWindows}
            checkDuplicates={checkDuplicates}
            peakY1={peakY1}
            setPeakY1={setPeakY1}
            peakY2={peakY2}
            setPeakY2={setPeakY2}
            valleyY1={valleyY1}
            setValleyY1={setValleyY1}
            valleyY2={valleyY2}
            setValleyY2={setValleyY2}
            calculateYLimit={calculateYLimit}
            twentyFourPlateDefinition={twentyFourPlateDefinition}
            setValleyLineDataToDefault={setValleyLineDataToDefault}
            setPeakLineDataToDefault={setPeakLineDataToDefault}
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
