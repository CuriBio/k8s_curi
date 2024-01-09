import styled from "styled-components";
import { useEffect } from "react";
import * as d3 from "d3";
import semverGte from "semver/functions/gte";

const Container = styled.div`
  background-color: white;
  position: relative;
  border-radius: 7px;
  height: 150px;
  width: 250px;
  margin-top: 15px;
  cursor: default;
`;

const WellNameLabel = styled.div`
  height: 18px;
  width: 100%;
  padding-left: 40px;
`;

const applyWindow = (data, xMin, xMax) => {
  const halfWindowedData = data.filter((coords) => coords[0] <= xMax);
  const windowEndIdx = halfWindowedData.length - 1;
  const dataWithinWindow = halfWindowedData.filter((coords) => coords[0] >= xMin);
  const windowStartIdx = halfWindowedData.length - dataWithinWindow.length;
  return { dataWithinWindow, windowStartIdx, windowEndIdx };
};

export default function BasicWaveformGraph({
  well,
  featureIndices,
  waveformData,
  timepointRange,
  pulse3dVersion,
}) {
  useEffect(() => {
    if (featureIndices) {
      // always remove existing graph before plotting new graph
      d3.select(`#waveformGraph${well}`).select("svg").remove();
      createGraph();
    }
  }, [waveformData, featureIndices]);

  // TODO remove this once we're done with RC versions
  const pulse3dSemver = pulse3dVersion.split("rc")[0];

  /* NOTE!! The order of the variables and function calls in this function are important to functionality.
     could eventually try to break this up, but it's more sensitive in react than vue */
  const createGraph = () => {
    const [peaks, valleys] = featureIndices;
    const { min: xMin, max: xMax } = timepointRange;

    /* --------------------------------------
        SET UP SVG GRAPH AND VARIABLES
      -------------------------------------- */

    console.log("###", timepointRange);

    const { dataWithinWindow } = applyWindow(waveformData, xMin, xMax);

    const waveformForFeatures = semverGte(pulse3dSemver, "1.0.0") ? dataWithinWindow : waveformData;

    const peaksWithinWindow = semverGte(pulse3dSemver, "1.0.0")
      ? peaks.filter((idx) => idx < dataWithinWindow.length)
      : peaks;
    const valleysWithinWindow = semverGte(pulse3dSemver, "1.0.0")
      ? valleys.filter((idx) => idx < dataWithinWindow.length)
      : valleys;
    console.log("$$$", dataWithinWindow.length, "---", peaksWithinWindow, valleysWithinWindow);

    const yMax = d3.max(dataWithinWindow, (d) => d[1]);
    const yMin = d3.min(dataWithinWindow, (d) => d[1]);
    // add .15 extra to y max and y min to auto scale the graph a little outside of true max and mins
    const yRange = yMax * 0.15;
    // nautilus/optical files seem to have really high y values that get cut off if left margin isn't large enough
    const leftMargin = yMax > 100000 ? 70 : 40;

    const margin = { top: 10, right: 10, bottom: 20, left: leftMargin },
      width = 250 - margin.left - margin.right,
      height = 150 - margin.top - margin.bottom;

    // Add X axis and Y axis
    const x = d3.scaleLinear().range([0, width]).domain([xMin, xMax]);

    const y = d3
      .scaleLinear()
      .range([height, 0])
      .domain([yMin - yRange, yMax + yRange]);

    // waveform line
    const dataLine = d3
      .line()
      .x((d) => {
        return x(d[0]);
      })
      .y((d) => {
        return y(d[1]);
      });

    // append the svg object to the body of the page
    const svg = d3
      .select(`#waveformGraph${well}`)
      .append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    /* --------------------------------------
        APPEND X AND Y AXES
      -------------------------------------- */
    svg.append("g").attr("transform", `translate(0, ${height})`).call(d3.axisBottom(x).ticks(10));

    svg.append("g").call(d3.axisLeft(y));

    /* --------------------------------------
        WAVEFORM TISSUE LINE
      -------------------------------------- */
    svg
      .append("path")
      .data([dataWithinWindow.map((x) => [x[0], x[1]])])
      .attr("fill", "none")
      .attr("stroke", "var(--curi-waveform)")
      .attr("stroke-width", 2)
      .attr("d", dataLine);

    /* --------------------------------------
        PEAKS AND VALLEYS
      -------------------------------------- */
    // graph all the peak markers
    svg
      .selectAll(`#waveformGraph${well}`)
      .data(peaksWithinWindow)
      .enter()
      .append("path")
      .attr("id", "peak")
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", (d) => {
        console.log("idx", d);
        return (
          "translate(" +
          x(waveformForFeatures[d][0]) +
          "," +
          (y(waveformForFeatures[d][1]) - 7) +
          ") rotate(180)"
        );
      })
      .style("fill", "var(--curi-peaks)")
      .attr("stroke", "var(--curi-peaks)")
      .style("display", (d) => {
        // only display them inside windowed analysis times
        const xTime = waveformForFeatures[d][0];
        return xTime > xMax || xTime < xMin ? "none" : null;
      });

    // graph all the valley markers
    svg
      .selectAll(`#waveformGraph${well}`)
      .data(valleysWithinWindow)
      .enter()
      .append("path")
      .attr("id", "valley")
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", (d) => {
        return "translate(" + x(waveformForFeatures[d][0]) + "," + (y(waveformForFeatures[d][1]) + 7) + ")";
      })
      .style("fill", "var(--curi-valleys)")
      .attr("stroke", "var(--curi-valleys)")
      .style("display", (d) => {
        // only display them inside windowed analysis times
        const xTime = waveformForFeatures[d][0];
        return xTime > xMax || xTime < xMin ? "none" : null;
      });

    /* --------------------------------------
        BLOCKERS (just top blocker for now)
      -------------------------------------- */
    svg
      .append("rect")
      .attr("x", -10)
      .attr("y", -margin.top)
      .attr("width", width + 15)
      .attr("height", margin.top)
      .attr("fill", "white")
      .style("overflow", "hidden");
  };

  return (
    <>
      <Container>
        <WellNameLabel>{well}</WellNameLabel>
        <div id={`waveformGraph${well}`} />
      </Container>
    </>
  );
}
