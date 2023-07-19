import { useEffect, useState } from "react";
import { getPeaksValleysFromTable, getWaveformCoordsFromTable, getTableFromParquet } from "@/utils/generic";

export const useWaveformData = (url) => {
  const [waveformData, setWaveformData] = useState([]);
  const [featureIndicies, setFeatureIndicies] = useState([]);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  const parseParquetData = async (data, tableFn, normalizeYAxis) => {
    const table = await getTableFromParquet(Object.values(JSON.parse(data)));
    return await tableFn(table, normalizeYAxis);
  };

  const getData = async () => {
    try {
      const response = await fetch(url);

      if (response.status !== 200) setError(true);
      else {
        const { peaksValleysData, normalizeYAxis, timeForceData } = await response.json();

        const featuresForWells = await parseParquetData(peaksValleysData, getPeaksValleysFromTable);
        const coordinates = await parseParquetData(timeForceData, getWaveformCoordsFromTable, normalizeYAxis);

        setWaveformData(coordinates);
        setFeatureIndicies(featuresForWells);
        setLoading(false);
      }
    } catch (e) {
      console.log("ERROR getting waveform data");
      setError(true);
    }
  };

  useEffect(() => {
    getData();
  }, [url]);

  return { waveformData, featureIndicies, getErrorState: error, getLoadingState: loading };
};
