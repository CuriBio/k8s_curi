import styled from "styled-components";
import { useEffect, useState } from "react";
import * as d3 from "d3";
// import ZoomWidget from "../basicWidgets/ZoomWidget";

const Container = styled.div`
  width: 1270px;
  height: 320px;
  background-color: white;
  overflow-x: scroll;
  border-radius: 7px;
  display: flex;
  flex-direction: row;
`;

const XAxisLabel = styled.div`
  top: 470px;
  left: 700px;
  font-size: 15px;
  overflow: hidden;
`;
const XAxisContainer = styled.div`
  position: relative;
  height: 50px;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const YAxisLabel = styled.div`
  position: relative;
  font-size: 15px;
  white-space: nowrap;
`;
const YAxisContainer = styled.div`
  position: relative;
  transform: rotate(-90deg);
  height: 50px;
  width: 50px;
  top: 35%;
  display: flex;
  align-items: center;
  justify-content: center;
`;

export default function WaveformGraph({
  dataToGraph,
  initialPeaksValleys,
  startTime,
  endTime,
  saveWellChanges,
}) {
  const [valleys, setValleys] = useState([]);
  const [peaks, setPeaks] = useState([]);
  const [newStartTime, setNewStartTime] = useState();
  const [newEndTime, setNewEndTime] = useState();

  const createGraph = () => {
    /* --------------------------------------
      SET UP SVG GRAPH AND VARIABLES
    -------------------------------------- */
    const maxTime = d3.max(dataToGraph, (d) => {
      return d[0];
    });

    const margin = { top: 20, right: 20, bottom: 30, left: 50 },
      width = 1270 - margin.left - margin.right,
      height = 300 - margin.top - margin.bottom;

    // currently sets 10 secs inside the graph window and multiples width to fit length of recording
    const widthMultiple = maxTime / 10 < 1 ? 1 : maxTime / 10;
    const dynamicWidth = width * widthMultiple;

    // append the svg object to the body of the page
    const svg = d3
      .select("#waveformGraph")
      .append("svg")
      .attr("width", dynamicWidth + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    // Add X axis and Y axis
    const x = d3
      .scaleLinear()
      .range([0, dynamicWidth])
      .domain(
        d3.extent(dataToGraph, (d) => {
          return d[0];
        })
      );

    // add .1 extra to y max and y min to auto scale the graph a little outside of true max and mins
    const yRange =
      d3.max(dataToGraph, (d) => {
        return d[1];
      }) * 0.1;

    const y = d3
      .scaleLinear()
      .range([height, 0])
      .domain([
        d3.min(dataToGraph, (d) => {
          return d[1];
        }) - yRange,
        d3.max(dataToGraph, (d) => {
          return d[1];
        }) + yRange,
      ]);

    console.log("OG: ", newStartTime, newEndTime);
    // calculate start and end times in pixels
    const initialStartTime = newStartTime ? x(newStartTime) : 0;
    const initialEndTime = newEndTime
      ? x(newEndTime)
      : x(
          d3.max(dataToGraph, (d) => {
            return d[0];
          })
        );

    // waveform line
    const dataLine = d3
      .line()
      .x((d) => {
        return x(d[0]);
      })
      .y((d) => {
        return y(d[1]);
      });

    // Create the text that travels along the curve of chart
    const focusText = svg
      .append("g")
      .append("text")
      .style("opacity", 0)
      .attr("text-anchor", "left")
      .attr("alignment-baseline", "middle");

    /* --------------------------------------
      X AND Y AXES
    -------------------------------------- */
    svg
      .append("g")
      .attr("transform", `translate(0, ${height})`)
      .call(d3.axisBottom(x).ticks(10 * widthMultiple));

    svg.append("g").call(d3.axisLeft(y));

    /* --------------------------------------
      WINDOW OF ANALYSIS FILLED BACKGROUND
    -------------------------------------- */
    // NOTE!! this needs to go before the tissue line, peaks, and valleys so that it sits behind them.
    const windowedAnalysisFill = svg
      .append("rect")
      .attr("fill", "pink")
      .attr("opacity", 0.2)
      .attr("x", initialStartTime)
      .attr("y", 0)
      .attr("height", height)
      .attr("width", initialEndTime - initialStartTime)
      .call(
        d3
          .drag()
          // NOTE!! these callbacks have to be in this syntax, not const () => {}
          .on("start", function (d) {
            d3.select(this)
              .attr("opacity", 0.4)
              .attr("cursor", "pointer")
              .attr(
                "startingPosFromLine",
                d3.pointer(d)[0] - parseFloat(startTimeLine.attr("x1"))
              );
          })
          .on("drag", function (d) {
            const startingPos = d3.select(this).attr("startingPosFromLine");
            const timeWidth = d3.select(this).attr("width");

            // make sure you can't drag outside of window bounds
            const position =
              d.x - startingPos < 0
                ? 0
                : d.x - startingPos + parseFloat(timeWidth) > dynamicWidth
                ? dynamicWidth - parseFloat(timeWidth)
                : d.x - startingPos;

            d3.select(this).attr("x", position);

            startTimeLine.attr("x1", position).attr("x2", position);

            endTimeLine
              .attr("x1", position + parseFloat(timeWidth))
              .attr("x2", position + parseFloat(timeWidth));
          })
          .on("end", function () {
            d3.select(this).attr("opacity", 0.2).attr("cursor", "default");
          })
      );

    /* --------------------------------------
      WAVEFORM TISSUE LINE
    -------------------------------------- */
    svg
      .append("path")
      .data([dataToGraph])
      .attr("fill", "none")
      .attr("stroke", "steelblue")
      .attr("stroke-width", 1.5)
      .attr("d", dataLine);

    /* --------------------------------------
      PEAKS AND VALLEYS
    -------------------------------------- */
    // NOTE!! these have to be in this syntax, not const () => {}
    function dragStarted() {
      // Makes the radius of the valley/peak marker larger when selected to show user
      d3.select(this).raise().attr("r", 10);
    }

    function dragging(d) {
      const peakOrValley = d3.select(this).attr("id");

      // invert gives the location of the mouse based on the x and y domains
      d[0] = x.invert(d.x);
      d[1] = y.invert(d.y);

      /* 
        To force circle to stay along data line, find index of x-coordinate in datapoints to then grab corresponding y-coordinate 
        If this is skipped, user will be able to drag circle anywhere on graph, unrelated to data line.
      */
      const draggedIdx = dataToGraph.findIndex(
        (x) => x[0] === Number(d[0].toFixed(2))
      );

      // assigns circle node new x and y coordinates based off drag event
      if (peakOrValley === "peak") {
        d3.select(this).attr(
          "transform",
          "translate(" +
            x(d[0]) +
            "," +
            (y(dataToGraph[draggedIdx][1]) - 7) +
            ") rotate(180)"
        );
      } else {
        d3.select(this).attr(
          "transform",
          "translate(" +
            x(d[0]) +
            "," +
            (y(dataToGraph[draggedIdx][1]) + 7) +
            ")"
        );
      }

      // update the focus text with current x and y data points as user drags marker
      focusText
        .html(
          "[ " +
            d[0].toFixed(2) +
            ", " +
            dataToGraph[draggedIdx][1].toFixed(2) +
            " ]"
        )
        .attr("x", x(d[0]) + 15)
        .attr("y", y(dataToGraph[draggedIdx][1]) + 15)
        .style("opacity", 1);
    }

    function dragEnded(d) {
      // Reduce marker radius and visual x/y markers once a user stops dragging.
      d3.select(this).attr("r", 6);
      focusText.style("opacity", 0);

      const peakOrValley = d3.select(this).attr("id");
      // indexToReplace is the index of the selected peak or valley in the peaks/valley state arrays that need to be changed
      const indexToChange = d3.select(this).attr("indexToReplace");
      const newSelectedIndex = dataToGraph.findIndex(
        (coords) => coords[0] === Number(x.invert(d.x).toFixed(2))
      );

      // TODO check here for alternating peaks and valleys, if not, return to original position and notify user
      if (peakOrValley === "peak") {
        peaks.splice(indexToChange, 1, newSelectedIndex);
      } else {
        valleys.splice(indexToChange, 1, newSelectedIndex);
      }
    }

    // graph all the peak markers
    svg
      .selectAll("#waveformGraph")
      .data(initialPeaksValleys[0])
      .enter()
      .append("path")
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", function (d) {
        return (
          "translate(" +
          x(dataToGraph[d][0]) +
          "," +
          (y(dataToGraph[d][1]) - 7) +
          ") rotate(180)"
        );
      })
      .attr("id", "peak")
      .attr("indexToReplace", (d) => initialPeaksValleys[0].indexOf(d))
      .style("fill", "orange")
      .attr("stroke", "orange")
      .style("cursor", "pointer")
      .call(
        d3
          .drag()
          .on("start", dragStarted)
          .on("drag", dragging)
          .on("end", dragEnded)
      );

    // graph all the valley markers
    svg
      .selectAll("#waveformGraph")
      .data(initialPeaksValleys[1])
      .enter()
      .append("path")
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", function (d) {
        return (
          "translate(" +
          x(dataToGraph[d][0]) +
          "," +
          (y(dataToGraph[d][1]) + 7) +
          ")"
        );
      })
      .attr("id", "valley")
      .attr("indexToReplace", (d) => initialPeaksValleys[1].indexOf(d))
      .style("fill", "green")
      .attr("stroke", "green")
      .style("cursor", "pointer")
      .call(
        d3
          .drag()
          .on("start", dragStarted)
          .on("drag", dragging)
          .on("end", dragEnded)
      );

    /* --------------------------------------
      START AND END TIME LINES
    -------------------------------------- */
    const lineDrag = d3
      .drag()
      .on("start", function () {
        // increase stroke width when selected and dragging
        d3.select(this).attr("stroke-width", 6);
      })
      .on("drag", function (d) {
        const time = d3.select(this).attr("id");
        const startingPos = startTimeLine.attr("x1");
        const endPos = endTimeLine.attr("x1");

        // ensure you can't move a line outside of window bounds
        let xPosition = d.x < 0 ? 0 : d.x > dynamicWidth ? dynamicWidth : d.x;

        // ensure start time cannot go above end time and vice versa
        if (time === "startTime" && d.x >= endPos) {
          xPosition = endPos;
        } else if (time === "endTime" && d.x <= startingPos) {
          xPosition = startingPos;
        }

        // assign new x values
        d3.select(this).attr("x1", xPosition).attr("x2", xPosition);

        // save adjusted time to pass up to parent component to use across all wells
        const newTimeSec = x.invert(xPosition);
        time === "startTime"
          ? setNewStartTime(newTimeSec)
          : setNewEndTime(newTimeSec);

        // adjust rectangle fill to new adjusted width
        windowedAnalysisFill
          .attr("x", startingPos)
          .attr("width", endPos - startingPos);
      })
      .on("end", function () {
        // descrease stroke width when unselected and dropped
        d3.select(this).attr("stroke-width", 5);
      });

    // start of window analysis line
    const startTimeLine = svg
      .append("line")
      .attr("id", "startTime")
      .attr("x1", initialStartTime)
      .attr("y1", 0)
      .attr("x2", initialStartTime)
      .attr("y2", height)
      .attr("stroke-width", 5)
      .attr("stroke", "black")
      .style("cursor", "pointer")
      .call(lineDrag);

    // end of window analysis line
    const endTimeLine = svg
      .append("line")
      .attr("id", "endTime")
      .attr("x1", initialEndTime)
      .attr("y1", 0)
      .attr("x2", initialEndTime)
      .attr("y2", height)
      .attr("stroke-width", 5)
      .attr("stroke", "black")
      .style("cursor", "pointer")
      .call(lineDrag);
  };

  useEffect(() => {
    // always remove existing graph before plotting new graph
    d3.select("#waveformGraph").select("svg").remove();

    if (initialPeaksValleys.length > 0) {
      setPeaks(initialPeaksValleys[0]);
      setValleys(initialPeaksValleys[1]);
      setNewStartTime(startTime);
      setNewEndTime(endTime);

      // console.log("INSDIE GRAPH");
      // console.log("PEAKS: ", peaks);
      // console.log("VALLEYS: ", valleys);
      createGraph();
    }

    return () => saveWellChanges(peaks, valleys, newStartTime, newEndTime);
  }, [dataToGraph, initialPeaksValleys]);

  return (
    <>
      <YAxisContainer>
        <YAxisLabel>Active Twitch Force (uN)</YAxisLabel>
        {/* <ZoomWidget size={"20px"} /> */}
      </YAxisContainer>
      <div>
        <Container>
          <div id="waveformGraph" />
        </Container>
        <XAxisContainer>
          <XAxisLabel>Time (seconds)</XAxisLabel>
          {/* <ZoomWidget size={"20px"} /> */}
        </XAxisContainer>
      </div>
    </>
  );
}
