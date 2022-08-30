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

export default function WaveformGraph({ dataToGraph }) {
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

    svg
      .append("path")
      .data([dataToGraph])
      .attr("class", "line")
      .attr("fill", "none")
      .attr("stroke", "steelblue")
      .attr("stroke-width", 1.5)
      .attr("d", valueLine);

    // This allows to find the closest X index of the mouse:
    const bisect = d3.bisector(function (d) {
      return d.x;
    }).left;

    // Create the circle that travels along the curve of chart
    const focus = svg
      .append("g")
      .append("circle")
      .style("fill", "none")
      .attr("stroke", "black")
      .attr("r", 8.5)
      .style("opacity", 0);

    // Create the text that travels along the curve of chart
    const focusText = svg
      .append("g")
      .append("text")
      .style("opacity", 0)
      .attr("text-anchor", "left")
      .attr("alignment-baseline", "middle");

    // Create a rect on top of the svg area: this rectangle recovers mouse position
    svg
      .append("rect")
      .style("fill", "none")
      .style("pointer-events", "all")
      .attr("width", width)
      .attr("height", height)
      .on("mouseover", mouseover)
      .on("mousemove", mousemove)
      .on("mouseout", mouseout)
      // .on("click", )

    const mouseover = () => {
      focus.style("opacity", 1);
      focusText.style("opacity", 1);
    };

    const mousemove = (e) => {
      // recover coordinate we need
      const x0 = Number(x.invert(d3.pointer(e, svg.node())[0]).toFixed(2));
      const selectedData = dataToGraph.find((x) => x[0] === x0);
      focus.attr("cx", x(selectedData[0])).attr("cy", y(selectedData[1]));
      focusText
        .html("[ " + selectedData[0] + ", " + selectedData[1].toFixed(2) + " ]")
        .attr("x", x(selectedData[0]) + 15)
        .attr("y", y(selectedData[1]));
    };

    const mouseout = () => {
      focus.style("opacity", 0);
      focusText.style("opacity", 0);
    };
  };

  useEffect(() => {
    // always remove existing graph before plotting new graph
    d3.select("#waveformGraph").select("svg").remove();
    createGraph();
  }, [dataToGraph]);

  return (
    <Container>
      <YAxisLabel>Active Twitch Force (uN)</YAxisLabel>
      <div id="waveformGraph" />
      <XAxisLabel>Time (seconds)</XAxisLabel>
    </Container>
  );
}
