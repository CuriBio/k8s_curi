import styled from "styled-components";
import { useEffect, useState } from "react";
import * as d3 from "d3";

const Container = styled.div`
  width: 1370px;
  height: 320px;
  background-color: white;
  overflow-x: scroll;
  border-radius: 7px;
  display: flex;
  flex-direction: row;
`;

const XAxisLabel = styled.div`
  position: fixed;
  top: 470px;
  left: 700px;
  font-size: 15px;
  overflow: hidden;
`;

const YAxisLabel = styled.div`
  position: relative;
  transform: rotate(-90deg);
  font-size: 15px;
  height: 20px;
  width: 20px;
  top: 200px;
  left: 10px;
  white-space: nowrap;
`;

export default function WaveformGraph({
  dataToGraph,
  initialPeaksValleys,
  startTime,
  endTime,
}) {
  const [valleys, setValleys] = useState([]);
  const [peaks, setPeaks] = useState([]);

  const createGraph = () => {
    const margin = { top: 20, right: 20, bottom: 30, left: 50 },
      width = 1350 - margin.left - margin.right,
      height = 300 - margin.top - margin.bottom;

    const dynamicWidth = width + 500;

    // append the svg object to the body of the page
    const svg = d3
      .select("#waveformGraph")
      .append("svg")
      .attr("width", dynamicWidth + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left},     ${margin.top})`);

    const windowedAnalysisFill = svg
      .append("rect")
      .attr("fill", "pink")
      .attr("opacity", 0.2)
      .attr("x", 0)
      .attr("y", 0)
      .attr("height", height)
      .attr("width", dynamicWidth-5)
      .call(
        d3
          .drag()
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

    // Add X axis and Y axis
    const x = d3
      .scaleLinear()
      .range([0, dynamicWidth])
      .domain(
        d3.extent(dataToGraph, (d) => {
          return d[0];
        })
      );
    const y = d3
      .scaleLinear()
      .range([height, 0])
      .domain([
        0,
        d3.max(dataToGraph, (d) => {
          return d[1];
        }),
      ]);

    svg
      .append("g")
      .attr("transform", `translate(0, ${height})`)
      .call(d3.axisBottom(x).ticks(15));

    svg.append("g").call(d3.axisLeft(y));

    // add the Line
    const valueLine = d3
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

    // append the tissue data line
    svg
      .append("path")
      .data([dataToGraph])
      .attr("fill", "none")
      .attr("stroke", "steelblue")
      .attr("stroke-width", 1.5)
      .attr("d", valueLine);

    function dragStarted() {
      // Makes the radius of the valley/peak marker larger when selected to show user
      d3.select(this).raise().attr("r", 10);
    }

    function dragging(d) {
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
      d3.select(this)
        .attr("cx", x(d[0]))
        .attr("cy", y(dataToGraph[draggedIdx][1]));

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
      .append("circle")
      .attr("id", "peak")
      .attr("indexToReplace", (d) => initialPeaksValleys[0].indexOf(d))
      .attr("cx", (d) => x(dataToGraph[d][0]))
      .attr("cy", (d) => y(dataToGraph[d][1]))
      .style("fill", "orange")
      .attr("stroke", "orange")
      .attr("r", 6)
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
      .append("circle")
      .attr("id", "valley")
      .attr("indexToReplace", (d) => initialPeaksValleys[1].indexOf(d))
      .attr("cx", (d) => x(dataToGraph[d][0]))
      .attr("cy", (d) => y(dataToGraph[d][1]))
      .style("fill", "green")
      .attr("stroke", "green")
      .style("cursor", "pointer")
      .attr("r", 6)
      .call(
        d3
          .drag()
          .on("start", dragStarted)
          .on("drag", dragging)
          .on("end", dragEnded)
      );

    const lineDrag = d3
      .drag()
      .on("start", function () {
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
        
        // adjust rectangle fill to new width
        windowedAnalysisFill
          .attr("x", startingPos)
          .attr("width", endPos - startingPos);
      })
      .on("end", function () {
        d3.select(this).attr("stroke-width", 5);
      });

    // start of window analysis line
    const startTimeLine = svg
      .append("line")
      .attr("id", "startTime")
      .attr("x1", 0)
      .attr("y1", 0)
      .attr("x2", 0)
      .attr("y2", height)
      .attr("stroke-width", 5)
      .attr("stroke", "black")
      .style("cursor", "pointer")
      .call(lineDrag);

    // end of window analysis line
    const endTimeLine = svg
      .append("line")
      .attr("id", "endTime")
      .attr("x1", dynamicWidth-5)
      .attr("y1", 0)
      .attr("x2", dynamicWidth-5)
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
      createGraph();
    }
  }, [dataToGraph, initialPeaksValleys]);

  return (
    <Container>
      <YAxisLabel>Active Twitch Force (uN)</YAxisLabel>
      <div id="waveformGraph" />
      <XAxisLabel>Time (seconds)</XAxisLabel>
    </Container>
  );
}
