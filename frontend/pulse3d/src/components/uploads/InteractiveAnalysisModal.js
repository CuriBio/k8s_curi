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
import semver from "semver";
const Container = styled.div`
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%),
    0px 8px 10px 1px rgb(0 0 0 / 20%), 0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const HeaderContainer = styled.div`
  font-size: 24px;
  margin: 20px;
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
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%),
    0px 8px 10px 1px rgb(0 0 0 / 20%), 0px 3px 14px 2px rgb(0 0 0 / 12%);
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
    messages: [
      "There was an issue while attempting to start this analysis.",
      "Please try again later.",
    ],
    buttons: ["Close"],
  },
  dataFound: {
    header: "Important!",
    messages: [
      "Previous changes have been found for this analysis.",
      "Do you want to use it or start over?",
    ],
    buttons: ["Start Over", "Use"],
  },
};

const wellNames = Array(24)
  .fill()
  .map((_, idx) => twentyFourPlateDefinition.getWellNameFromIndex(idx));

export default function InteractiveWaveformModal({
  selectedJob,
  setOpenInteractiveAnalysis,
}) {
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
  const [xRange, setXRange] = useState({
    min: null,
    max: null, // random
  });
  const [editableStartEndTimes, setEditableStartEndTimes] = useState({
    startTime: null,
    endTime: null,
  });

  const { pulse3dVersions } = useContext(UploadsContext);

  const getWaveformData = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/waveform_data?upload_id=${selectedJob.uploadId}&job_id=${selectedJob.jobId}`
      );

      if (response.status === 200) {
        const waveformData = await response.json();
        // original data is set and never changed to hold original state in case of reset
        setOriginalData(waveformData);
        setEditablePeaksValleys(waveformData.peaks_valleys);
      } else {
        // open error modal and kick users back to /uploads page if random  error
        setModalLabels(constantModalLabels.error);
        setModalOpen("status");
      }
    } catch (e) {
      console.log("ERROR getting waveform data: ", e);
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
    setEditableStartEndTimes({
      startTime: existingData.editableStartEndTimes.startTime,
      endTime: existingData.editableStartEndTimes.endTime,
    });
  };

  useEffect(() => {
    const compatibleVersions = pulse3dVersions.filter((v) =>
      semver.satisfies(v, ">=0.25.2")
    );

    setFilteredVersions([...compatibleVersions]);
    checkForExistingData();
    // set to hold state of start and stop original times
    setXRange({
      min: selectedJob.analysisParams.start_time,
      max: selectedJob.analysisParams.end_time,
    });
  }, [selectedJob]);

  useEffect(() => {
    updateChangelog();
  }, [markers, editableStartEndTimes]);

  useEffect(() => {
    // will error on init because there won't be an index 0
    if (Object.keys(originalData).length > 0) {
      setDataToGraph([...originalData.coordinates[selectedWell]]);
    }
  }, [selectedWell, originalData]);

  useEffect(() => {
    if (dataToGraph.length > 0) {
      setMarkers([...editablePeaksValleys[selectedWell]]);
      setIsLoading(false);
    }
  }, [dataToGraph, editablePeaksValleys]);

  const handleWellSelection = (idx) => {
    setSelectedWell(wellNames[idx]);
  };

  const resetWellChanges = () => {
    // reset peaks and valleys for current well
    editablePeaksValleys[selectedWell] =
      originalData.peaks_valleys[selectedWell];

    // reset state
    setEditablePeaksValleys({ ...editablePeaksValleys });
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

      const jobResponse = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs`,
        {
          method: "POST",
          body: JSON.stringify(requestBody),
        }
      );
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
    if (modalOpen === "status") setOpenInteractiveAnalysis(false);
    else if (i === 0) getNewData();
    else loadExistingData();

    setModalOpen(false);
    sessionStorage.removeItem(selectedJob.jobId);
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

    if (changelog[selectedWell] && markers.length === 2) {
      const wellChanges = changelog[selectedWell];
      const { peaks, valleys, startTime, endTime } =
        wellChanges[wellChanges.length - 1];

      if (JSON.stringify(peaks) !== JSON.stringify(markers[0])) {
        const diffIdx = peaks.findIndex(
          (peakIdx, i) => peakIdx !== markers[0][i]
        );
        changelogMessage = `Peak at [ ${
          dataToGraph[peaks[diffIdx]]
        } ] was moved to [ ${dataToGraph[markers[0][diffIdx]]} ]`;
      } else if (JSON.stringify(valleys) !== JSON.stringify(markers[1])) {
        const diffIdx = valleys.findIndex(
          (valleyIdx, i) => valleyIdx !== markers[1][i]
        );
        changelogMessage = `Valley at [ ${
          dataToGraph[valleys[diffIdx]]
        } ] was moved to [ ${dataToGraph[markers[1][diffIdx]]} ].`;
      } else if (startTime !== editableStartEndTimes.startTime) {
        changelogMessage = `Start time was changed from ${startTime} to ${editableStartEndTimes.startTime}.`;
      } else if (endTime !== editableStartEndTimes.endTime) {
        changelogMessage = `End time was changed from ${endTime} to ${editableStartEndTimes.endTime}.`;
      }
      if (changelogMessage !== undefined) {
        changelog[selectedWell].push({
          peaks: markers[0],
          valleys: markers[1],
          startTime: editableStartEndTimes.startTime,
          endTime: editableStartEndTimes.endTime,
          message: changelogMessage,
        });
      }
    } else if (
      markers.length === 2 &&
      originalData.peaks_valleys[selectedWell]
    ) {
      const ogWellData = originalData.peaks_valleys[selectedWell];

      if (JSON.stringify(ogWellData[0]) !== JSON.stringify(markers[0])) {
        const diffIdx = ogWellData[0].findIndex(
          (peakIdx, i) => peakIdx !== markers[0][i]
        );
        changelogMessage = `Peak at [ ${
          dataToGraph[ogWellData[0][diffIdx]]
        } ] was moved to [ ${dataToGraph[markers[0][diffIdx]]} ].`;
      } else if (JSON.stringify(ogWellData[1]) !== JSON.stringify(markers[1])) {
        const diffIdx = ogWellData[1].findIndex(
          (peakIdx, i) => peakIdx !== markers[0][i]
        );
        changelogMessage = `Valley at [ ${
          dataToGraph[ogWellData[1][diffIdx]]
        } ] was moved to [ ${dataToGraph[markers[1][diffIdx]]} ].`;
      } else if (xRange.min !== editableStartEndTimes.startTime) {
        changelogMessage = `Start time was changed from ${xRange.min} to ${editableStartEndTimes.startTime}.`;
      } else if (xRange.max !== editableStartEndTimes.endTime) {
        changelogMessage = `End time was changed from ${xRange.max} to ${editableStartEndTimes.endTime}.`;
      }
      if (changelogMessage !== undefined) {
        changelog[selectedWell] = [
          {
            peaks: markers[0],
            valleys: markers[1],
            startTime: editableStartEndTimes.startTime,
            endTime: editableStartEndTimes.endTime,
            message: changelogMessage,
          },
        ];
      }
    }
  };

  const deletePeakValley = (peakValley, idx) => {
    const typeIdx = ["peak", "valley"].indexOf(peakValley);
    const targetIdx = editablePeaksValleys[selectedWell][typeIdx].indexOf(idx);
    if (targetIdx > -1) {
      // remove desired marker
      editablePeaksValleys[selectedWell][typeIdx].splice(targetIdx, 1);
      setEditablePeaksValleys({ ...editablePeaksValleys });
      setMarkers([...editablePeaksValleys[selectedWell]]);
    }
  };

  const addPeakValley = (peakValley, targetTime) => {
    const typeIdx = ["peak", "valley"].indexOf(peakValley);

    const indexToAdd = dataToGraph.findIndex(
      (coord) => Number(coord[0].toFixed(2)) === Number(targetTime.toFixed(2))
    );

    editablePeaksValleys[selectedWell][typeIdx].push(indexToAdd);
    setEditablePeaksValleys({ ...editablePeaksValleys });
    setMarkers([...editablePeaksValleys[selectedWell]]);
  };

  const handleVersionSelect = (idx) => {
    setPulse3dVersionIdx(idx);
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
            />
          </GraphContainer>
          <ErrorLabel>{errorMessage}</ErrorLabel>
          <VersionDropdownContainer>
            <VersionDropdownLabel htmlFor="selectedPulse3dVersion">
              Pulse3d Version:
              <Tooltip
                title={
                  <TooltipText>
                    {
                      "Specifies which version of the pulse3d analysis software to use."
                    }
                  </TooltipText>
                }
              >
                <InfoOutlinedIcon />
              </Tooltip>
            </VersionDropdownLabel>
            <DropDownWidget
              options={filteredVersions}
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
              backgroundColor={
                uploadInProgress ? "var(--dark-gray)" : "var(--dark-blue)"
              }
              disabled={uploadInProgress}
              inProgress={uploadInProgress}
              clickFn={postNewJob}
            />
          </ButtonContainer>
        </>
      )}
      <ModalWidget
        open={["status", "dataFound"].includes(modalOpen)}
        buttons={modalLabels.buttons}
        closeModal={handleModalClose}
        header={modalLabels.header}
        labels={modalLabels.messages}
      />
    </Container>
  );
}
