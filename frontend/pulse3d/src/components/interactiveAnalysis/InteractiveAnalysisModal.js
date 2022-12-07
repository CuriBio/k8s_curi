import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import DropDownWidget from "../basicWidgets/DropDownWidget";
import WaveformGraph from "./WaveformGraph";
import { WellTitle as LabwareDefinition } from "@/utils/labwareCalculations";
import CircularSpinner from "../basicWidgets/CircularSpinner";
const twentyFourPlateDefinition = new LabwareDefinition(4, 6);
import ButtonWidget from "../basicWidgets/ButtonWidget";
import ModalWidget from "../basicWidgets/ModalWidget";
import { UploadsContext } from "@/components/layouts/DashboardLayout";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";
import semverGte from "semver/functions/gte";

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

const VersionDropdownContainer = styled.div`
  height: 30px;
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 300px;
`;

const VersionDropdownLabel = styled.span`
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
  align-items: center;
  margin-bottom: 45px;
`;
const ButtonContainer = styled.div`
  position: relative;
  height: 50px;
  width: 100%;
  top: 6vh;
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
  oldPulse3dVersion: {
    header: "Warning!",
    messages: [
      "Interactive analysis is using a newer version of Pulse3D than the version originally used on this recording. Peaks and valleys may be slightly different.",
      "Please re-analyze this recording using a Pulse3D version greater than 0.28.0 or continue.",
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

export default function InteractiveWaveformModal({ selectedJob, setOpenInteractiveAnalysis }) {
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

  const [xRange, setXRange] = useState({
    min: null,
    max: null,
  });
  const [editableStartEndTimes, setEditableStartEndTimes] = useState({
    startTime: null,
    endTime: null,
  });

  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);

  useEffect(() => {
    // only available for versions greater than 0.25.2
    const compatibleVersions = pulse3dVersions.filter((v) => semverGte(v, "0.25.2"));
    setFilteredVersions([...compatibleVersions]);

    // check sessionStorage for saved data
    checkForExistingData();
  }, [selectedJob]);

  useEffect(() => {
    // updates changelog when peaks/valleys and start/end times change
    if (!undoing) updateChangelog();
    else setUndoing(false);
  }, [markers, editableStartEndTimes]);

  useEffect(() => {
    // will error on init because there won't be an index 0
    if (Object.keys(originalData).length > 0) {
      const wellData = originalData.coordinates[selectedWell];
      const { start_time, end_time } = selectedJob.analysisParams;
      // update x min and max if no start or end time was ever defined so it isn't null in changelog messages
      setXRange({
        min: start_time ? start_time : Math.min(...wellData.map((coords) => coords[0])),
        max: end_time ? end_time : Math.max(...wellData.map((coords) => coords[0])),
      });

      setDataToGraph([...wellData]);
    }
  }, [selectedWell, originalData]);

  useEffect(() => {
    if (dataToGraph.length > 0) {
      setMarkers([...editablePeaksValleys[selectedWell]]);
      setIsLoading(false);
    }
  }, [dataToGraph, editablePeaksValleys]);

  const getWaveformData = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/waveform_data?upload_id=${selectedJob.uploadId}&job_id=${selectedJob.jobId}`
      );

      if (response.status === 200) {
        const res = await response.json();
        if (!res.error) {
          // original data is set and never changed to hold original state in case of reset
          setOriginalData(res);
          setEditablePeaksValleys(res.peaks_valleys);

          if (!res.orig_pulse3d_version) {
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

  const getNewData = async () => {
    await getWaveformData();
    setEditableStartEndTimes({
      startTime: selectedJob.analysisParams.start_time,
      endTime: selectedJob.analysisParams.end_time,
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
  };

  const handleWellSelection = (idx) => {
    setSelectedWell(wellNames[idx]);
  };

  const resetWellChanges = () => {
    // reset peaks and valleys for current well
    const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
    const changelogCopy = JSON.parse(JSON.stringify(changelog));

    peaksValleysCopy[selectedWell] = originalData.peaks_valleys[selectedWell];
    changelogCopy[selectedWell] = [];
    // reset state
    setEditablePeaksValleys(peaksValleysCopy);
    setChangelog(changelogCopy);
  };

  const postNewJob = async () => {
    try {
      setUploadInProgress(true);

      // reassign new peaks and valleys if different
      const requestBody = {
        ...selectedJob.analysisParams,
        upload_id: selectedJob.uploadId,
        peaks_valleys: editablePeaksValleys,
        start_time: editableStartEndTimes.startTime,
        end_time: editableStartEndTimes.endTime,
        version: filteredVersions[pulse3dVersionIdx],
      };

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
      console.log("ERROR posting new job");
      setModalLabels(constantModalLabels.error);
      setUploadInProgress(false);
      setModalOpen("status");
    }
  };

  const handleModalClose = (i) => {
    if (modalOpen !== "pulse3dWarning") {
      if (modalOpen === "status") setOpenInteractiveAnalysis(false);
      else if (i === 0) getNewData();
      else loadExistingData();
      sessionStorage.removeItem(selectedJob.jobId);
    }
    setModalOpen(false);
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
      })
    );
  };

  const updateChangelog = () => {
    let changelogMessage;

    // changelog will have length of 0 if a user Undo's until initial state
    if (changelog[selectedWell] && changelog[selectedWell].length > 0 && markers.length === 2) {
      const wellChanges = changelog[selectedWell];
      const { peaks, valleys, startTime, endTime } = wellChanges[wellChanges.length - 1];

      changelogMessage = getChangelogMessage(peaks, valleys, startTime, endTime);
    } else if (markers.length === 2 && originalData.peaks_valleys[selectedWell]) {
      const ogWellData = originalData.peaks_valleys[selectedWell];
      changelogMessage = getChangelogMessage(ogWellData[0], ogWellData[1], xRange.min, xRange.max);
    }

    if (changelogMessage !== undefined) {
      addToChangelog(changelogMessage);
    }
  };

  const getChangelogMessage = (peaksToCompare, valleysToCompare, startToCompare, endToCompare) => {
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
      windowedTimeDiff = startTimeDiff && endTimeDiff;

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
      changelogMessage = `Start time was changed from ${startToCompare.toFixed(
        2
      )} to ${editableStartEndTimes.startTime.toFixed(
        2
      )} and end time was changed from ${endToCompare.toFixed(2)} to ${editableStartEndTimes.endTime.toFixed(
        2
      )}.`;
    } else if (startTimeDiff) {
      changelogMessage = `Start time was changed from ${startToCompare.toFixed(
        2
      )} to ${editableStartEndTimes.startTime.toFixed(2)}.`;
    } else if (endTimeDiff) {
      changelogMessage = `End time was changed from ${endToCompare.toFixed(
        2
      )} to ${editableStartEndTimes.endTime.toFixed(2)}.`;
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

    changelog[selectedWell].push({
      peaks: peaksValleysCopy[selectedWell][0],
      valleys: peaksValleysCopy[selectedWell][1],
      startTime,
      endTime,
      message,
    });

    setChangelog({ ...changelog });
  };

  const handleVersionSelect = (idx) => {
    setPulse3dVersionIdx(idx);
  };

  const undoLastChange = () => {
    if (changelog[selectedWell] && changelog[selectedWell].length > 0) {
      // undoing state tells the updateChangelog useEffect to not ignore the change and not as a new change
      setUndoing(true);
      // make copies so you control when state is updated
      const changesCopy = JSON.parse(JSON.stringify(changelog[selectedWell]));
      const peaksValleysCopy = JSON.parse(JSON.stringify(editablePeaksValleys));
      const newWindowTimes = {};

      // remove step with latest changes
      changesCopy.pop();

      if (changesCopy.length > 0) {
        // grab state from the step before the undo step to set as current state
        const { peaks, valleys, startTime, endTime } = changesCopy[changesCopy.length - 1];
        // set old peaks and valleys to well
        peaksValleysCopy[selectedWell] = [[...peaks], [...valleys]];

        newWindowTimes.startTime = startTime;
        newWindowTimes.endTime = endTime;
      } else {
        // if only one change was made, then you revert back to original state
        newWindowTimes.startTime = xRange.min;
        newWindowTimes.endTime = xRange.max;

        peaksValleysCopy[selectedWell] = originalData.peaks_valleys[selectedWell];
      }

      // needs to be reassigned to hold state
      changelog[selectedWell] = changesCopy;
      // update values to state to rerender graph
      setEditableStartEndTimes(newWindowTimes);
      setEditablePeaksValleys(peaksValleysCopy);
      setChangelog(changelog);
    }
  };

  return (
    <Container>
      <HeaderContainer>Interactive Waveform Analysis</HeaderContainer>
      {isLoading ? (
        <SpinnerContainer>
          <CircularSpinner size={300} />
        </SpinnerContainer>
      ) : (
        <>
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
            />
          </GraphContainer>
          <ErrorLabel>{errorMessage}</ErrorLabel>
          <VersionDropdownContainer>
            <VersionDropdownLabel htmlFor="selectedPulse3dVersion">
              Pulse3d Version:
              <Tooltip
                title={
                  <TooltipText>
                    {"Specifies which version of the pulse3d analysis software to use."}
                  </TooltipText>
                }
              >
                <InfoOutlinedIcon sx={{ "&:hover": { color: "var(--teal-green)", cursor: "pointer" } }} />
              </Tooltip>
            </VersionDropdownLabel>
            <DropDownWidget
              options={filteredVersions.map((version) => {
                const selectedVersionMeta = metaPulse3dVersions.filter((meta) => meta.version === version);
                return selectedVersionMeta[0] && selectedVersionMeta[0].state === "testing"
                  ? version + " " + "[ testing ]"
                  : version;
              })}
              label="Select"
              reset={pulse3dVersionIdx === 0}
              handleSelection={handleVersionSelect}
              initialSelected={0}
            />
          </VersionDropdownContainer>
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
              backgroundColor={uploadInProgress ? "var(--dark-gray)" : "var(--dark-blue)"}
              disabled={uploadInProgress}
              inProgress={uploadInProgress}
              clickFn={postNewJob}
            />
          </ButtonContainer>
        </>
      )}
      <ModalWidget
        open={["status", "dataFound", "pulse3dWarning"].includes(modalOpen)}
        buttons={modalLabels.buttons}
        closeModal={handleModalClose}
        header={modalLabels.header}
        labels={modalLabels.messages}
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
    </Container>
  );
}
