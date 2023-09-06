import { useEffect, useState } from "react";
import { getPeaksValleysFromTable, getWaveformCoordsFromTable, getTableFromParquet } from "@/utils/generic";

export const useWaveformData = (url) => {
  const [waveformData, setWaveformData] = useState([]);
  const [featureIndices, setFeatureIndicies] = useState([]);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  const parseParquetData = async (data, tableFn) => {
    const table = await getTableFromParquet(Object.values(JSON.parse(data)));
    return await tableFn(table);
  };

  const getData = async () => {
    try {
      const response = await fetch(url);

      if (response.status !== 200) setError(true);
      else {
        const { peaksValleysData, timeForceData } = await response.json();

        const featuresForWells = await parseParquetData(peaksValleysData, getPeaksValleysFromTable);
        const coordinates = await parseParquetData(timeForceData, getWaveformCoordsFromTable);

        setWaveformData(coordinates);
        setFeatureIndicies(featuresForWells);
        setLoading(false);
      }
    } catch (e) {
      console.log("ERROR getting waveform data: ", e);
      setError(true);
    }
  };

  useEffect(() => {
    getData();
  }, [url]);

  return { waveformData, featureIndices, getErrorState: error, getLoadingState: loading };
};
