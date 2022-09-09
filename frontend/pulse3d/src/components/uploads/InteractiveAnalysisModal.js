import styled from "styled-components";
import { useEffect, useState } from "react";
import DropDownWidget from "../basicWidgets/DropDownWidget";
import WaveformGraph from "./WaveformGraph";
import { WellTitle as LabwareDefinition } from "@/utils/labwareCalculations";
import CircularSpinner from "../basicWidgets/CircularSpinner";
const twentyFourPlateDefinition = new LabwareDefinition(4, 6);
import ButtonWidget from "../basicWidgets/ButtonWidget";

const Container = styled.div`
  height: 700px;
  display: flex;
  flex-direction: column;
  align-items: center;
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
`;

export default function InteractiveWaveformModal({
  selectedJob,
  setOpenInteractiveAnalysis,
}) {
  const [selectedWell, setSelectedWell] = useState("A1");
  const [originalData, setOriginalData] = useState([]); // original waveform data from GET request, unedited
  const [dataToGraph, setDataToGraph] = useState([]); // well-specfic coordinates to graph
  const [isLoading, setIsLoading] = useState(true);
  const [markers, setMarkers] = useState([]); // peak and valleyy markers
  const [editablePeaksValleys, setEditablePeaksValleys] = useState(); // user edited peaks/valleys as changes are made, should get stored in localStorage
  const [editableStartEndTimes, setEditableStartEndTimes] = useState({
    startTime: null,
    endTime: null,
  });

  const getWaveformData = async () => {
    try {
      const response = await fetch(
        `https://curibio.com/uploads/waveform_data?upload_id=${selectedJob.uploadId}`
      );

      const waveformData = await response.json();
      setOriginalData(waveformData);
      setEditablePeaksValleys(waveformData.peaks_valleys);

      setIsLoading(false);
    } catch (e) {
      console.log("ERROR getting waveform data: ", e);
    }
  };

  useEffect(() => {
    getWaveformData();
    setEditableStartEndTimes({
      startTime: selectedJob.analysisParams.start_time,
      endtime: selectedJob.analysisParams.end_time,
    });
  }, [selectedJob]);

  useEffect(() => {
    // will error on init because there won't be an index 0
    if (originalData && Object.keys(originalData).length > 0) {
      setDataToGraph([...originalData.coordinates[selectedWell]]);
      setMarkers([...editablePeaksValleys[selectedWell]]);
    }
  }, [originalData, selectedWell]);

  const wellNames = Array(24)
    .fill()
    .map((_, idx) => twentyFourPlateDefinition.getWellNameFromIndex(idx));

  const handleWellSelection = (idx) => {
    setSelectedWell(wellNames[idx]);
  };

  const saveWellChanges = (peaks, valleys, startTime, endTime) => {
    // console.log("INSIDE FUNCTION");
    // console.log("PEAKS: ", peaks);
    // console.log("VALLEYS: ", valleys);
    console.log("START: ", startTime);
    console.log("END: ", endTime);
    setEditableStartEndTimes({
      startTime: startTime || editableStartEndTimes.startTime,
      endTime: endTime || editableStartEndTimes.endTime,
    });

    const newPeaksValleys = editablePeaksValleys;
    newPeaksValleys[selectedWell] = [[...peaks], [...valleys]];
    setEditablePeaksValleys(newPeaksValleys);
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
              initialSelected={0}
            />
          </DropdownContainer>
          <GraphContainer>
            <WaveformGraph
              dataToGraph={dataToGraph}
              initialPeaksValleys={markers}
              startTime={editableStartEndTimes.startTime}
              endTime={editableStartEndTimes.endTime}
              saveWellChanges={saveWellChanges}
            />
          </GraphContainer>
          <ButtonContainer>
            <ButtonWidget
              width="150px"
              height="50px"
              position="relative"
              borderRadius="3px"
              left="70px"
              // backgroundColor={
              //   isButtonDisabled ? "var(--dark-gray)" : "var(--dark-blue)"
              // }
              // disabled={isButtonDisabled}
              // inProgress={inProgress}
              label="Cancel"
              clickFn={() => setOpenInteractiveAnalysis(false)}
            />

            <ButtonWidget
              width="150px"
              height="50px"
              position="relative"
              borderRadius="3px"
              left="890px"
              // backgroundColor={
              //   isButtonDisabled ? "var(--dark-gray)" : "var(--dark-blue)"
              // }
              // disabled={isButtonDisabled}
              // inProgress={inProgress}
              label="Reset All"
              // clickFn={checkForMultiRecZips}
            />

            <ButtonWidget
              width="150px"
              height="50px"
              position="relative"
              borderRadius="3px"
              left="900px"
              // backgroundColor={
              //   isButtonDisabled ? "var(--dark-gray)" : "var(--dark-blue)"
              // }
              // disabled={isButtonDisabled}
              // inProgress={inProgress}
              label="Run Analysis"
              // clickFn={checkForMultiRecZips}
            />
          </ButtonContainer>
        </>
      )}
    </Container>
  );
}
