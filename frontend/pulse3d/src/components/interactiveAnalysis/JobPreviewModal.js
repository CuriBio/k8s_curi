import styled from "styled-components";
import { useEffect, useState, useContext, useMemo } from "react";
import BasicWaveformGraph from "@/components/interactiveAnalysis/BasicWaveformGraph";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import { getPeaksValleysFromTable, getWaveformCoordsFromTable, getTableFromParquet } from "@/utils/generic";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import { useWaveformData } from "@/components/interactiveAnalysis//useWaveformData";

import { WellTitle as LabwareDefinition } from "@/utils/labwareCalculations";
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

const GraphContainer = styled.div`
  width: 94%;
  left: 1%;
  position: relative;
  display: grid;
  overflow-y: hidden;
  overflow-x: scroll;
  padding-bottom: 30px;
  grid-template-columns: repeat(6, auto);
  grid-template-rows: repeat(4, auto);
  grid-template-areas:
    "A1 A2 A3 A4 A5 A6"
    "B1 B2 B3 B4 B5 B6"
    "C1 C2 C3 C4 C5 C6"
    "D1 D2 D3 D4 D5 D6";
  &::-webkit-scrollbar {
    height: 15px;
    background-color: var(--dark-gray);
  }
  &::-webkit-scrollbar-thumb {
    background-color: var(--dark-blue);
    cursor: pointer;
  }
  &::-webkit-scrollbar-thumb:hover {
    background-color: var(--teal-green);
  }
`;

const SpinnerContainer = styled.div`
  height: 550px;
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: center;
`;

const ButtonContainer = styled.div`
  height: 100px;
  width: 100%;
  display: flex;
  justify-content: right;
  padding: 25px 100px;
`;

const XAxisContainer = styled.div`
  height: 50px;
  padding: 20px;
  width: 100%;
  display: flex;
  flex-direction: row;
  position: relative;
`;

const XAxisLine = styled.hr`
  width: 50%;
  margin: 9px 4%;
`;

const YAxisContainer = styled.div`
  width: 3%;
  position: relative;
  padding: 0 25px;
  display: flex;
  justify-content: end;
  flex-direction: column;
`;

const YAxisLabel = styled.div`
  position: relative;
  transform: rotate(-90deg);
  height: 31%;
  width: 190px;
  line-height: 2.5;
`;

const YAxisLine = styled.hr`
  height: 50%;
`;

const GraphAxisContainer = styled.div`
  width: 100%;
  display: flex;
  flex-direction: row;
`;

const wellNames = Array(24)
  .fill()
  .map((_, idx) => twentyFourPlateDefinition.getWellNameFromIndex(idx));

const errorModalLabels = {
  header: "Error Occurred!",
  messages: ["There was an issue getting the data for this analysis.", "Please try again later."],
  buttons: ["Close"],
};

export default function JobPreviewModal({
  selectedAnalysis: { jobId, uploadId, analysisParams },
  setOpenJobPreview,
}) {
  // const [waveformData, setWaveformData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [timepointRange, setTimepointRange] = useState([]);
  // const [featureIndicies, setFeatureIndicies] = useState([]);
  const [openErrorModal, setOpenErrorModal] = useState(false);
  const { waveformData, featureIndicies, error, loading } = useWaveformData(
    `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/waveform-data?upload_id=${uploadId}&job_id=${jobId}`
  );

  useEffect(() => {
    if (error) setOpenErrorModal(true);
    else if (!loading) {
      getTimepointRange(waveformData["A1"]);
      setIsLoading(false);
    }
  }, [error, loading]);

  const getTimepointRange = async (coordinates) => {
    const { start_time } = analysisParams;
    const min = start_time || Math.min(...coordinates.map((coords) => coords[0]));
    // because it's a snapshot, you only need 10 seconds
    const max = min + 10;

    setTimepointRange({ min, max });
  };

  return (
    <>
      <Container>
        {isLoading ? (
          <SpinnerContainer>
            <CircularSpinner size={200} color={"secondary"} />
          </SpinnerContainer>
        ) : (
          <>
            <GraphAxisContainer>
              <YAxisContainer>
                <YAxisLabel>Active Twitch Force (uN)</YAxisLabel>
                <YAxisLine />
              </YAxisContainer>
              <GraphContainer>
                {wellNames.map((well) => (
                  <div key={well} style={{ position: "relative", gridArea: well }}>
                    <BasicWaveformGraph
                      well={well}
                      timepointRange={timepointRange}
                      waveformData={waveformData[well]}
                      featureIndicies={featureIndicies[well]}
                    />
                  </div>
                ))}
              </GraphContainer>
            </GraphAxisContainer>
            <XAxisContainer>
              <XAxisLine />
              <div>Time (s)</div>
            </XAxisContainer>
          </>
        )}

        <ButtonContainer>
          <ButtonWidget
            width="200px"
            height="45px"
            position="relative"
            borderRadius="3px"
            label="Close"
            disabled={isLoading}
            backgroundColor={isLoading ? "var(--dark-gray)" : "var(--dark-blue)"}
            clickFn={() => setOpenJobPreview(false)}
          />
        </ButtonContainer>
      </Container>
      <ModalWidget
        open={openErrorModal}
        buttons={errorModalLabels.buttons}
        closeModal={() => setOpenJobPreview(false)}
        header={errorModalLabels.header}
        labels={errorModalLabels.messages}
      />
    </>
  );
}
