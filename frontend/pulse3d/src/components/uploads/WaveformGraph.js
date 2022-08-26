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
