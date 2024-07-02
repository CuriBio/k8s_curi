import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import BasicWaveformGraph from "@/components/interactiveAnalysis/BasicWaveformGraph";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import CircularSpinner from "@/components/basicWidgets/CircularSpinner";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import { useWaveformData } from "@/components/interactiveAnalysis//useWaveformData";
import { AuthContext } from "@/pages/_app";

const Container = styled.div`
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2%;
  overflow: hidden;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%), 0px 8px 10px 1px rgb(0 0 0 / 20%),
    0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const GraphContainer = styled.div`
  width: 94%;
  left: 1%;
  position: relative;
  display: grid;
  overflow-y: scroll;
  overflow-x: scroll;
  padding-bottom: 30px;
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
  white-space: nowrap;
`;

const YAxisLine = styled.hr`
  height: 50%;
`;

const GraphAxisContainer = styled.div`
  width: 100%;
  display: flex;
  flex-direction: row;
  max-height: 890px;
`;

const errorModalLabels = {
  header: "Error Occurred!",
  messages: ["There was an issue getting the data for this analysis.", "Please try again later."],
  buttons: ["Close"],
};

export default function JobPreviewModal({ selectedAnalysis: { jobId, analysisParams }, setOpenJobPreview }) {
  const [isLoading, setIsLoading] = useState(true);
  const [timepointRange, setTimepointRange] = useState([]);
  const [openErrorModal, setOpenErrorModal] = useState(false);
  const [gridStyle, setGridStyle] = useState({});

  const { productPage, accountType } = useContext(AuthContext);

  const { waveformData, featureIndices, getErrorState, getLoadingState, yAxisLabel } = useWaveformData(
    `${process.env.NEXT_PUBLIC_PULSE3D_URL}/jobs/waveform-data?job_id=${jobId}&upload_type=${productPage}`,
    analysisParams.normalization_method,
    accountType === "admin" ? "mantarray" : productPage // TODO need to figure out how to handle this for admins
  );

  useEffect(() => {
    if (getErrorState) {
      setOpenErrorModal(true);
    } else if (!getLoadingState) {
      // first well may not be A1 if optical files, so just grab first value
      getGridStyle();
      getTimepointRange(waveformData[Object.keys(waveformData)[0]]);
      setIsLoading(false);
    }
  }, [getErrorState, getLoadingState]);

  const getTimepointRange = async (coordinates) => {
    const { start_time, end_time } = analysisParams;

    const minTimeInData = Math.min(...coordinates.map((coords) => coords[0]));
    const maxTimeInData = Math.max(...coordinates.map((coords) => coords[0]));

    const min = start_time || minTimeInData;
    // because it's a snapshot, you only need 10 seconds
    const max = Math.min(min + 10, end_time || maxTimeInData);

    setTimepointRange({ min, max });
  };

  const getGridStyle = () => {
    const numOfWells = Object.keys(waveformData).length;

    let numRows, numCols;
    if (numOfWells <= 24) {
      numRows = 4;
      numCols = 6;
    } else if (numOfWells > 24 && numOfWells <= 96) {
      numRows = 8;
      numCols = 12;
    } else if (numOfWells > 96 && numOfWells <= 384) {
      numRows = 16;
      numCols = 24;
    } else if (numOfWells > 384) {
      numRows = 32;
      numCols = 48;
    }

    const areas = [...Array(numRows)].map((_, rowIdx) => {
      return [...Array(numCols)].map((_, colIdx) => `well${rowIdx + colIdx * numRows}`).join(" ");
    });

    setGridStyle({
      gridTemplateColumns: `repeat(${numCols}, auto)`,
      gridTemplateRows: `repeat(${numRows}, auto)`,
      gridTemplateAreas: `"${areas.join('" "')}`,
    });
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
                <YAxisLabel>
                  {Object.keys(waveformData).length > 1 && (
                    <div style={{ transform: "rotate(-90deg)" }}>{yAxisLabel}</div>
                  )}
                </YAxisLabel>
                <YAxisLine />
              </YAxisContainer>
              <GraphContainer style={gridStyle}>
                {Object.keys(waveformData).map((well, i) => (
                  <div key={well} style={{ position: "relative", gridArea: `well${i}` }}>
                    <BasicWaveformGraph
                      well={well}
                      timepointRange={timepointRange}
                      waveformData={waveformData[well]}
                      featureIndices={featureIndices[well]}
                      pulse3dVersion={analysisParams.pulse3d_version}
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
