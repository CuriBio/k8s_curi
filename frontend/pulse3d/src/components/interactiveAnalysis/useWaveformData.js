import { useEffect, useState } from "react";
import { getPeaksValleysFromTable, getWaveformCoordsFromTable, getTableFromParquet } from "@/utils/generic";

export const useWaveformData = (url, normalizationMethod, productPage) => {
  const [waveformData, setWaveformData] = useState([]);
  const [featureIndices, setFeatureIndices] = useState([]);
  const [yAxisLabel, setYAxisLabel] = useState();
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
        const { peaksValleysData, amplitudeLabel, timeForceData } = await response.json();

        const featuresForWells = await parseParquetData(peaksValleysData, getPeaksValleysFromTable);
        const coordinates = await parseParquetData(timeForceData, (table) =>
          getWaveformCoordsFromTable(table, normalizationMethod, productPage)
        );

        setWaveformData(coordinates);
        setFeatureIndices(featuresForWells);
        setYAxisLabel(amplitudeLabel || "Active Twitch Force (µN)");
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

  return { waveformData, featureIndices, getErrorState: error, getLoadingState: loading, yAxisLabel };
};
