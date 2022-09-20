import styled from "styled-components";
import { useEffect, useState } from "react";
import DropDownWidget from "../basicWidgets/DropDownWidget";
import WaveformGraph from "./WaveformGraph";
import { WellTitle as LabwareDefinition } from "@/utils/labwareCalculations";
import CircularSpinner from "../basicWidgets/CircularSpinner";
const twentyFourPlateDefinition = new LabwareDefinition(4, 6);
import ButtonWidget from "../basicWidgets/ButtonWidget";
import ModalWidget from "../basicWidgets/ModalWidget";

const Container = styled.div`
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
`;

const HeaderContainer = styled.div`
  font-size: 24px;
  margin: 20px;
`;

const DropdownContainer = styled.div`
  height: 30px;
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 200px;
`;

const DropdownLabel = styled.span`
  line-height: 2;
  font-size: 20px;
  white-space: nowrap;
  padding-right: 15px;
`;

const GraphContainer = styled.div`
  height: 390px;
  border-radius: 7px;
  background-color: var(--med-gray);
  position: relative;
  width: 1350px;
  margin-top: 4%;
  overflow: hidden;
  padding: 15px;
  display: flex;
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
  top: 8vh;
  display: flex;
  justify-content: space-evenly;
`;

const uploadModalLabels = {
  success: {
    header: "Success!",
    messages: [
      "You have successfully started a new analysis.",
      "It will appear in the uploads table shortly.",
    ],
  },
  error: {
    header: "Error Occurred!",
    messages: [
      "There was an issue while attempting to start this analysis.",
      "Please try again later.",
    ],
  },
};

export default function InteractiveWaveformModal({
  selectedJob,
  setOpenInteractiveAnalysis,
}) {
  const [selectedWell, setSelectedWell] = useState("A1");
  const [uploadInProgress, setUploadInProgress] = useState(false);
  const [originalData, setOriginalData] = useState({}); // original waveform data from GET request, unedited
  const [dataToGraph, setDataToGraph] = useState([]); // well-specfic coordinates to graph
  const [isLoading, setIsLoading] = useState(true);
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [modalLabels, setModalLabels] = useState(uploadModalLabels.success);
  const [markers, setMarkers] = useState([]); // peak and valleyy markers
  const [editablePeaksValleys, setEditablePeaksValleys] = useState(); // user edited peaks/valleys as changes are made, should get stored in localStorage
  const [xRange, setXRange] = useState({
    min: null,
    max: null, // random
  });
  const [editableStartEndTimes, setEditableStartEndTimes] = useState({
    startTime: null,
    endTime: null,
  });

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
        setModalLabels(uploadModalLabels.error);
        setStatusModalOpen(true);
      }
    } catch (e) {
      console.log("ERROR getting waveform data: ", e);
    }
  };

  useEffect(() => {
    getWaveformData();
    setEditableStartEndTimes({
      startTime: selectedJob.analysisParams.start_time,
      endTime: selectedJob.analysisParams.end_time,
    });
    // set to hold state of start and stop original times
    setXRange({
      min: selectedJob.analysisParams.start_time,
      max: selectedJob.analysisParams.end_time,
    });
  }, [selectedJob]);

  useEffect(() => {
    if (!uploadInProgress && Object.keys(originalData).length > 0) {
      setStatusModalOpen(true);
    }
  }, [uploadInProgress]);

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

  const wellNames = Array(24)
    .fill()
    .map((_, idx) => twentyFourPlateDefinition.getWellNameFromIndex(idx));

  const handleWellSelection = (idx) => {
    setSelectedWell(wellNames[idx]);
  };

  const resetAllChanges = () => {
    // reset start and end times
    setEditableStartEndTimes({
      startTime: selectedJob.analysisParams.start_time,
      endTime: selectedJob.analysisParams.end_time,
    });
    // reset dropdown to "A1"
    handleWellSelection(0);
    // reset peaks and valleys
    setEditablePeaksValleys({ ...originalData.peaks_valleys });
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
        version: selectedJob.version
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
        setModalLabels(uploadModalLabels.error);
      } else {
        setModalLabels(uploadModalLabels.success);
      }

      setUploadInProgress(false);
    } catch (e) {
      // TODO make modal
      console.log("ERROR posting new job");
      setModalLabels(uploadModalLabels.error);
      setUploadInProgress(false);
    }
  };

  const closeInteractiveAnalysis = () => {
    setOpenInteractiveAnalysis(false);
    setStatusModalOpen(false);
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
          <DropdownContainer>
            <DropdownLabel>Select Well:</DropdownLabel>
            <DropDownWidget
              options={wellNames}
              handleSelection={handleWellSelection}
              reset={selectedWell == "A1"}
              initialSelected={0}
            />
          </DropdownContainer>
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
            />
          </GraphContainer>
          <ButtonContainer>
            <ButtonWidget
              width="150px"
              height="50px"
              position="relative"
              borderRadius="3px"
              left="-100px"
              label="Cancel"
              clickFn={() => setOpenInteractiveAnalysis(false)}
            />

            <ButtonWidget
              width="150px"
              height="50px"
              position="relative"
              borderRadius="3px"
              left="320px"
              label="Reset All"
              backgroundColor={
                uploadInProgress ? "var(--dark-gray)" : "var(--dark-blue)"
              }
              disabled={uploadInProgress}
              clickFn={resetAllChanges}
            />

            <ButtonWidget
              width="150px"
              height="50px"
              position="relative"
              borderRadius="3px"
              left="100px"
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
        open={statusModalOpen}
        closeModal={closeInteractiveAnalysis}
        header={modalLabels.header}
        labels={modalLabels.messages}
      />
    </Container>
  );
}
