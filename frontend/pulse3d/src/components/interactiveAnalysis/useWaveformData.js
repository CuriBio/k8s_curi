import { useEffect, useState } from "react";
import { getPeaksValleysFromTable, getWaveformCoordsFromTable, getTableFromParquet } from "@/utils/generic";

export const useWaveformData = (url) => {
  const [waveformData, setWaveformData] = useState([]);
  const [featureIndicies, setFeatureIndicies] = useState([]);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchFromS3 = async (presignedUrl, tableFn, normalizeYAxis) => {
    const response = await fetch(presignedUrl);
    const buffer = new Uint8Array(await response.arrayBuffer());
    const table = await getTableFromParquet(Object.values(buffer));

    return await tableFn(table, normalizeYAxis);
  };

  const getData = async () => {
    try {
      const response = await fetch(url);

      if (response.status !== 200) setError(true);
      else {
        const { timeForceUrl, peaksValleysUrl, normalizeYAxis } = await response.json();

        const featuresForWells = await fetchFromS3(peaksValleysUrl, getPeaksValleysFromTable);
        const coordinates = await fetchFromS3(timeForceUrl, getWaveformCoordsFromTable, normalizeYAxis);

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

  return { waveformData, featureIndicies, getErrorState: error, getLoadingState: loading };
};
