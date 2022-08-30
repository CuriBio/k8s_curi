import styled from "styled-components";
import { useEffect, useState } from "react";
import DropDownWidget from "../basicWidgets/DropDownWidget";
import WaveformGraph from "./WaveformGraph";
import { WellTitle as LabwareDefinition } from "@/utils/labwareCalculations";
import CircularSpinner from "../basicWidgets/CircularSpinner";
const twentyFourPlateDefinition = new LabwareDefinition(4, 6);

const Container = styled.div`
  height: 700px;
  display: flex;
  flex-direction: column;
  align-items: center;
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
  height: 350px;
  border-radius: 7px;
  background-color: var(--med-gray);
  position: relative;
  width: 1400px;
  margin-top: 4%;
  overflow: hidden;
  padding: 15px;
`;

const SpinnerContainer = styled.div`
  height: 100%;
  display: flex;
  align-items: center;
  margin-bottom: 45px;
`;

export default function InteractiveWaveformModal({ uploadId }) {
  const [selectedWell, setSelectedWell] = useState(0);
  const [data, setData] = useState([]);
  const [dataToGraph, setDataToGraph] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const getWaveformData = async () => {
    try {
      const response = await fetch(
        `https://curibio.com/uploads/waveform_data?upload_id=${uploadId}`
      );
      const { coordinates, peaks_valleys } = await response.json();
      console.log(JSON.stringify(peaks_valleys));
      setData([...coordinates]);
      setIsLoading(false);
    } catch (e) {
      console.log("ERROR getting waveform data: ", e);
    }
  };

  useEffect(() => {
    getWaveformData();
  }, [uploadId]);

  useEffect(() => {
    // will error on init because there won't be an index 0
    if (data.length > 0) setDataToGraph([...data[selectedWell]]);
  }, [data, selectedWell]);

  const wellNames = Array(24)
    .fill()
    .map((_, idx) => twentyFourPlateDefinition.getWellNameFromIndex(idx));

  const handleWellSelection = (idx) => {
    setSelectedWell(idx);
  };

  return (
    <Container>
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
            <WaveformGraph dataToGraph={dataToGraph} />
          </GraphContainer>
        </>
      )}
    </Container>
  );
}
