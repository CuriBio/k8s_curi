import { useEffect, useState } from "react";
import { getPeaksValleysFromTable, getWaveformCoordsFromTable, getTableFromParquet } from "@/utils/generic";

export const useWaveformData = (url) => {
  const [waveformData, setWaveformData] = useState([]);
  const [featureIndicies, setFeatureIndicies] = useState([]);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(async () => {
    setLoading(true);
    const wasmModule = await import("parquet-wasm/esm/arrow1.js");
    await wasmModule.default();

    const response = await fetch(url);

    if (response.status !== 200) setError(true);
    else {
      const buffer = await response.json();

      const featuresTable = await getTableFromParquet(Object.values(buffer.peaksValleys));
      const featuresForWells = await getPeaksValleysFromTable(featuresTable);

      const timeForceTable = await getTableFromParquet(Object.values(buffer.timeForceData));
      const coordinates = await getWaveformCoordsFromTable(timeForceTable, buffer.normalizeYAxis);

      setWaveformData(coordinates);
      setFeatureIndicies(featuresForWells);
      setLoading(false);
    }
  }, [url]);

  return { waveformData, featureIndicies, error, loading };
};
