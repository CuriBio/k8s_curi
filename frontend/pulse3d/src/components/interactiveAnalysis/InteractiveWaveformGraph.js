import styled from "styled-components";
import { useEffect, useState } from "react";
import * as d3 from "d3";
import ZoomWidget from "@/components/basicWidgets/ZoomWidget";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";
import MenuItem from "@mui/material/MenuItem";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import semverGte from "semver/functions/gte";

const Container = styled.div`
  width: 1260px;
  height: 328px;
  background-color: white;
  overflow-x: scroll;
  overflow-y: scroll;
  position: relative;
  left: 50px;
  bottom: 0px;
  border-radius: 7px;
  display: flex;
  flex-direction: row;
  &::-webkit-scrollbar {
    height: 15px;
    background-color: var(--dark-gray);
  }
  &::-webkit-scrollbar-thumb {
    background-color: var(--dark-blue);
    cursor: pointer;
  }
  &::-webkit-scrollbar-thumb:hover {
    background-color: var(--teal-green);
  }
`;

const CursorLocLabel = styled.div`
  font-size: 15px;
  cursor: default;
  width: 200px;
  text-align: center;
`;

const TooltipText = styled.span`
  font-size: 15px;
`;

const ColumnContainer = styled.div`
  position: relative;
  bottom: 25px;
`;

const XAxisLabel = styled.div`
  top: 470px;
  left: 700px;
  font-size: 15px;
  overflow: hidden;
  line-height: 2;
  margin-right: 3px;
`;

const XAxisContainer = styled.div`
  position: relative;
  width: 100%;
  margin-top: 14px;
  margin-bottom: -9px;
  display: flex;
  align-items: center;
  justify-content: space-around;
`;

const YAxisLabel = styled.div`
  position: relative;
  font-size: 15px;
  white-space: nowrap;
`;
const YAxisContainer = styled.div`
  position: relative;
  transform: rotate(-90deg);
  width: 50px;
  top: 186px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
`;

const ToolbarContainer = styled.div`
  position: relative;
  height: 40px;
  display: flex;
  flex-direction: row;
  width: 100%;
  justify-content: flex-end;
  font-size: 16px;
  align-items: center;
  padding-right: 35px;
  padding-bottom: 4px;
`;

const HowTo = styled.div`
  width: 180px;
  display: flex;
  line-height: 1.5;
  justify-content: space-between;
  padding-right: 10px;
  cursor: default;
`;

const ContextMenuContainer = styled.div`
  font-size: 16px;
  background-color: white;
  display: none;
  border-radius: 6px;
  box-shadow: 2px 2px 2px 0px rgb(0 0 0 / 20%), 5px 5px 5px 5px rgb(0 0 0 / 10%);
`;

const ChangelogLabel = styled.div`
  font-size: 16px;
  font-style: italic;
  right: 600px;
  position: relative;
  &:hover {
    color: var(--teal-green);
    cursor: pointer;
  }
`;
const Legend = styled.div`
  background-color: white;
  width: 800px;
  padding: 5px;
  margin-left: 21px;
  border-radius: 10px;
  border: 2px solid darkgray;
  & table {
    display: flex;
    flex-flow: column;
  }
  & table tr {
    display: flex;
    align-items: flex-end;
    justify-content: space-evenly;
  }
  & table tr td {
    font-size: 0.75rem;
    display: flex;
    flex-flow: column;
    align-items: center;
  }
`;

const Triangle = styled.div`
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-${(props) => props.direction}: 13px solid ${(props) => {
  if (props.type === "peak") {
    return "var(--curi-peaks)";
  } else if (props.type === "valley") {
    return "var(--curi-valleys)";
  } else {
    return "var(--curi-error-markers)";
  }
}};
`;
const LineColor = styled.div`
  height: 3px;
  width: 50px;
  background-color: ${(props) => (props.type === "peak" ? "var(--curi-peaks)" : "var(--curi-valleys)")};
`;
const LineAdjuster = styled.div`
  height: 14px;
  width: 14px;
  border-radius: 50%;
  background-color: ${(props) => (props.type === "peak" ? "var(--curi-peaks)" : "var(--curi-valleys)")};
`;
const ToRowComponent = styled.div`
  display: flex;
  align-items: center;
`;

const contextMenuItems = {
  moveDelete: ["Move", "Delete"],
  add: ["Add Peak", "Add Valley"],
};

const NoFeaturesAlert = styled.div`
  color: red;
`;

const applyWindow = (data, xMin, xMax) => {
  const halfWindowedData = data.filter((coords) => coords[0] <= xMax);
  const windowEndIdx = halfWindowedData.length - 1;
  const dataWithinWindow = halfWindowedData.filter((coords) => coords[0] >= xMin);
  const windowStartIdx = halfWindowedData.length - dataWithinWindow.length;
  return { dataWithinWindow, windowStartIdx, windowEndIdx };
};

export default function WaveformGraph({
  timepointRange,
  waveformData,
  customAnalysisSettings,
  customAnalysisSettingsUpdaters,
  changelogActions,
  yAxisLabel,
  prevPulse3dVersion,
}) {
  const {
    windowedAnalysisBounds: { start: startTime, end: endTime },
    featureIndices: { peaks, valleys },
    duplicateIndices,
    thresholdEndpoints,
  } = customAnalysisSettings;

  const [menuItems, setMenuItems] = useState(contextMenuItems.moveDelete);
  const [selectedMarkerToMove, setSelectedMarkerToMove] = useState();
  const [cursorLoc, setCursorLoc] = useState([0, 0]);
  const [xZoomFactor, setXZoomFactor] = useState(1);
  const [yZoomFactor, setYZoomFactor] = useState(1);

  useEffect(() => {
    // manually scrolls graph div to bottom because the graph div expands down instead of up
    const containerToScroll = document.getElementById("scrollableContainer");
    containerToScroll.scrollTop = containerToScroll.scrollHeight;
  }, [yZoomFactor]);

  useEffect(() => {
    if (peaks && valleys) {
      // always remove existing graph before plotting new graph
      d3.select("#waveformGraph").select("svg").remove();
      createGraph();
    }
  }, [customAnalysisSettings, selectedMarkerToMove, xZoomFactor, yZoomFactor, startTime, endTime]);

  const getClosestIndex = (coordinates, x) => {
    const time = coordinates.map((x) => x[0]);
    const closestValue = time.sort(
      (a, b) =>
        Math.abs(Number(x.toFixed(2)) - Number(a.toFixed(2))) -
        Math.abs(Number(x.toFixed(2)) - Number(b.toFixed(2)))
    )[0];

    return coordinates.findIndex((x) => Number(x[0].toFixed(2)) === Number(closestValue.toFixed(2)));
  };

  /* NOTE!! The order of the variables and function calls in this function are important to functionality.
     could eventually try to break this up, but it's more sensitive in react than vue */
  const createGraph = () => {
    /* --------------------------------------
        SET UP SVG GRAPH AND VARIABLES
      -------------------------------------- */
    const maxTime = d3.max(waveformData, (d) => {
      return d[0];
    });

    // if windowed analysis, use else use recording max and min times
    const xMin = timepointRange.min || waveformData[0][0];
    const xMax = timepointRange.max || maxTime;

    const margin = { top: 20, right: 20, bottom: 30, left: 50 },
      width = 1245 - margin.left - margin.right,
      height = 300 - margin.top - margin.bottom;

    // TODO handle if zoom becomes smaller than smallest component width
    const dynamicWidth = Math.max(width, width * xZoomFactor);
    const dynamicHeight = Math.max(height, height * yZoomFactor);
    // Add X axis and Y axis
    const x = d3.scaleLinear().range([0, dynamicWidth]).domain([xMin, xMax]);

    const { dataWithinWindow } = applyWindow(waveformData, xMin, xMax);
    const waveformForFeatures = semverGte(prevPulse3dVersion, "1.0.0") ? dataWithinWindow : waveformData;

    const yMax = d3.max(dataWithinWindow, (d) => d[1]);
    const yMin = d3.min(dataWithinWindow, (d) => d[1]);
    // add .15 extra to y max and y min to auto scale the graph a little outside of true max and mins
    const yRange = yMax * 0.15;

    const y = d3
      .scaleLinear()
      .range([dynamicHeight, 0])
      .domain([yMin - yRange, yMax + yRange]);
    // calculate start and end times in pixels. If windowed time found, use, else recording max and min
    const initialStartTime = x(startTime || xMin);
    const initialEndTime = x(endTime || maxTime);
    // helper functions
    function appendFeatureMarkers(id, lineId, xRaw, yRaw, color) {
      return svg
        .append("circle")
        .attr("id", id)
        .attr("lineId", lineId)
        .attr("r", 6)
        .attr("cx", x(xRaw))
        .attr("cy", y(yRaw))
        .attr("fill", color)
        .attr("stroke", color)
        .style("cursor", "pointer")
        .call(pivotLineDrag);
    }
    // waveform line
    const dataLine = d3
      .line()
      .x((d) => {
        return x(d[0] / xZoomFactor);
      })
      .y((d) => {
        return y(d[1] / yZoomFactor);
      });

    // setup custom  context menu
    const contextMenu = d3.select("#contextmenu");

    // append the svg object to the body of the page
    const svg = d3
      .select("#waveformGraph")
      .append("svg")
      .attr("width", dynamicWidth + margin.left + margin.right)
      .attr("height", dynamicHeight + margin.top + margin.bottom)
      .on("mousemove", (e) => {
        // creates static cursor coordinates in lower right hand corner
        setCursorLoc([
          x.invert(e.offsetX - 50).toFixed(2), // counteract the margins
          y.invert(e.offsetY - 20).toFixed(2), // counteract the margins
        ]);
      })
      .on("mousedown", () => {
        contextMenu.style("display", "none");
        if (selectedMarkerToMove) {
          // if set, remove selection on click elsewhere
          setSelectedMarkerToMove();
        }
      })
      .on("contextmenu", (e) => {
        e.preventDefault();
      })
      .on("mouseout", () => {
        // resets coordinates when user exits components with mouse
        setCursorLoc([0, 0]);
      })
      .append("g")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    d3.select("body").on("keydown", (e) => {
      // handles key presses globally, haven't found a diff way to do it
      if ([37, 39].includes(e.keyCode) && selectedMarkerToMove) {
        e.preventDefault();

        const { type, idx } = selectedMarkerToMove;

        const shiftAmount = e.keyCode === 37 ? -1 : 1;
        const features = type === "peak" ? peaks : valleys;
        const idxVal = features[idx];

        customAnalysisSettingsUpdaters.moveFeature(`${type}s`, idxVal, idxVal + shiftAmount);
      }
    });

    // Create the text that travels along the curve of chart
    const focusText = svg
      .append("g")
      .append("text")
      .style("opacity", 0)
      .attr("text-anchor", "left")
      .attr("alignment-baseline", "middle");

    if (selectedMarkerToMove) {
      const features = selectedMarkerToMove.type === "peak" ? peaks : valleys;
      const coords = waveformForFeatures[features[selectedMarkerToMove.idx]];

      focusText
        .html("[ " + coords[0].toFixed(2) + ", " + coords[1].toFixed(2) + " ]")
        .attr("x", x(coords[0]) + 15)
        .attr("y", y(coords[1]) - 20)
        .style("opacity", 1)
        .style("z-index", 5);
    }

    /* --------------------------------------
        APPEND X AND Y AXES
      -------------------------------------- */
    svg
      .append("g")
      .attr("transform", `translate(0, ${dynamicHeight})`)
      .call(d3.axisBottom(x).ticks(10 * xZoomFactor));

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
      .attr("height", dynamicHeight)
      .attr("width", initialEndTime - initialStartTime)
      .call(
        d3
          .drag()
          // NOTE!! these callbacks have to be in this syntax, not const () => {}
          .on("start", function (d) {
            // close context menu if it's open
            contextMenu.style("display", "none");
            if (selectedMarkerToMove) {
              // if set, remove selection on click elsewhere
              setSelectedMarkerToMove();
            }

            d3.select(this)
              .attr("opacity", 0.4)
              .attr("cursor", "pointer")
              .attr("startingPosFromLine", d3.pointer(d)[0] - parseFloat(startTimeLine.attr("x1")));
          })
          .on("drag", function (d) {
            const startingPos = parseFloat(d3.select(this).attr("startingPosFromLine"));
            const timeWidth = parseFloat(d3.select(this).attr("width"));
            // make sure you can't drag outside of window bounds
            const newStartPosition = Math.min(Math.max(d.x - startingPos, 0), dynamicWidth - timeWidth);

            d3.select(this).attr("x", newStartPosition);

            // reposition start time, peaks, valleys lines and set value to state
            startTimeLine.attr("x1", newStartPosition).attr("x2", newStartPosition);
            valleyThresholdLine.attr("x1", newStartPosition);
            peakThresholdLine.attr("x1", newStartPosition);
            peaksY1.attr("cx", x(x.invert(newStartPosition) + endpointMarkerOffset));
            valleysY1.attr("cx", x(x.invert(newStartPosition) + endpointMarkerOffset));

            // reposition end time, peaks, valleys lines and set value to state
            const endPosition = newStartPosition + timeWidth;
            endTimeLine.attr("x1", endPosition).attr("x2", endPosition);
            valleyThresholdLine.attr("x2", endPosition);
            peakThresholdLine.attr("x2", endPosition);
            peaksY2.attr("cx", x(x.invert(endPosition) - endpointMarkerOffset));
            valleysY2.attr("cx", x(x.invert(endPosition) - endpointMarkerOffset));
          })
          .on("end", function () {
            const timeWidth = parseFloat(d3.select(this).attr("width"));
            const startPosition = parseFloat(d3.select(this).attr("x"));
            const endPosition = startPosition + timeWidth;
            // save new window analysis times to state on end so that it only updates changelog on drop
            customAnalysisSettingsUpdaters.setWindowBounds({
              start: parseFloat(x.invert(startPosition).toFixed(2)),
              end: parseFloat(x.invert(endPosition).toFixed(2)),
            });
            d3.select(this).attr("opacity", 0.2).attr("cursor", "default");
          })
      );

    /* --------------------------------------
        WAVEFORM TISSUE LINE
      -------------------------------------- */
    svg
      .append("path")
      .data([waveformForFeatures.map((x) => [x[0] * xZoomFactor, x[1] * yZoomFactor])])
      .attr("fill", "none")
      .attr("stroke", "var(--curi-waveform)")
      .attr("stroke-width", 2)
      .attr("d", dataLine)
      .style("cursor", "pointer")
      .on("contextmenu", (e) => {
        e.preventDefault();
        const timepoint = x.invert(e.offsetX - 50);
        const isWithinTimeWindow = timepoint > startTime && timepoint < endTime;
        // prevents context menu from appearing if its outside the windowed analysis lines to prevent confusion if no peak or valley gets visibly added
        if (isWithinTimeWindow) {
          setMenuItems(contextMenuItems.add);
          contextMenu
            .attr("target", timepoint) // gives context menu easy access to target peak/valley
            .style("position", "absolute")
            .style("left", e.layerX + 80 + "px") // layer does not take in scroll component so x and y stay within visible window
            .style("top", e.layerY + 50 + "px")
            .style("display", "block");
        }
      });

    /* --------------------------------------
        PEAKS AND VALLEYS
      -------------------------------------- */
    // NOTE!! these have to be in this syntax, not const () => {}  -- not sure why yet
    function dragStarted(d) {
      // close context menu if it's open
      contextMenu.style("display", "none");
      // Makes the radius of the valley/peak marker larger when selected to show user
      d3.select(this).raise().attr("r", 10);
    }

    function dragging(d) {
      const featureType = d3.select(this).attr("id");

      // sets static cursor coordinates to empty because marker already has coordinates when dragging
      setCursorLoc(["_ ", "_"]);
      // invert gives the location of the mouse based on the x and y domains
      d[0] = x.invert(d.x);
      d[1] = y.invert(d.y);

      /*
        To force circle to stay along data line, find index of x-coordinate in datapoints to then grab corresponding y-coordinate
        If this is skipped, user will be able to drag circle anywhere on graph, unrelated to data line.
      */
      const draggedIdx = getClosestIndex(waveformForFeatures, d[0]);
      // assigns circle node new x and y coordinates based off drag event
      if (featureType === "peak") {
        d3.select(this).attr(
          "transform",
          "translate(" + x(d[0]) + "," + (y(waveformForFeatures[draggedIdx][1]) - 7) + ") rotate(180)"
        );
      } else {
        d3.select(this).attr(
          "transform",
          "translate(" + x(d[0]) + "," + (y(waveformForFeatures[draggedIdx][1]) + 7) + ")"
        );
      }
      // update the focus text with current x and y data points as user drags marker
      focusText
        .html("[ " + d[0].toFixed(2) + ", " + waveformForFeatures[draggedIdx][1].toFixed(2) + " ]")
        .attr("x", x(d[0]) + 15)
        .attr("y", y(waveformForFeatures[draggedIdx][1]) - 20)
        .style("opacity", 1);
    }

    function dragEnded(d) {
      // Reduce marker radius and visual x/y markers once a user stops dragging.
      d3.select(this).attr("r", 6);
      focusText.style("opacity", 0);

      const featureType = d3.select(this).attr("id");
      const features = featureType === "peak" ? peaks : valleys;
      // indexToReplace is the index of the selected peak or valley in the peaks/valley state arrays that need to be changed
      const indexToChange = features[d3.select(this).attr("indexToReplace")];
      const newSelectedIndex = getClosestIndex(waveformForFeatures, x.invert(d.x));

      customAnalysisSettingsUpdaters.moveFeature(`${featureType}s`, indexToChange, newSelectedIndex);
    }

    // graph all the peak markers
    svg
      .selectAll("#waveformGraph")
      .data(peaks)
      .enter()
      .append("path")
      .attr("id", "peak")
      .attr("indexToReplace", (d) => peaks.indexOf(d)) // keep track of index in peaks array to splice later
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", (d) => {
        return (
          "translate(" +
          x(waveformForFeatures[d][0]) +
          "," +
          (y(waveformForFeatures[d][1]) - 7) +
          ") rotate(180)"
        );
      })
      .style("fill", (d) => {
        return duplicateIndices.peaks.includes(d) ? "var(--curi-error-markers)" : "var(--curi-peaks)";
      })
      .attr("stroke", (d) => {
        return duplicateIndices.peaks.includes(d) ? "var(--curi-error-markers)" : "var(--curi-peaks)";
      })
      .style("cursor", "pointer")
      .style("display", (d) => {
        // only display them inside windowed analysis times
        const xTime = waveformForFeatures[d][0];
        return xTime > xMax || xTime < xMin ? "none" : null;
      })
      .on("contextmenu", (e, i) => {
        e.preventDefault();
        setMenuItems(contextMenuItems.moveDelete);
        contextMenu
          .attr("target", i) // gives context menu easy access to target peak/valley
          .attr("type", "peak")
          .style("position", "absolute")
          .style("left", e.layerX + 80 + "px") // layer does not take in scroll component so x and y stay within visible window
          .style("top", e.layerY + 50 + "px")
          .style("display", "block");
      })
      .call(d3.drag().on("start", dragStarted).on("drag", dragging).on("end", dragEnded));

    // graph all the valley markers
    svg
      .selectAll("#waveformGraph")
      .data(valleys)
      .enter()
      .append("path")
      .attr("id", "valley")
      .attr("indexToReplace", (d) => valleys.indexOf(d)) // keep track of index in valleys array to splice later
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", (d) => {
        return "translate(" + x(waveformForFeatures[d][0]) + "," + (y(waveformForFeatures[d][1]) + 7) + ")";
      })
      .style("fill", (d) => {
        return duplicateIndices.valleys.includes(d) ? "var(--curi-error-markers)" : "var(--curi-valleys)";
      })
      .attr("stroke", (d) => {
        return duplicateIndices.valleys.includes(d) ? "var(--curi-error-markers)" : "var(--curi-valleys)";
      })
      .style("cursor", "pointer")
      .style("display", (d) => {
        // only display them inside windowed analysis times
        const xTime = waveformForFeatures[d][0];
        return xTime > xMax || xTime < xMin ? "none" : null;
      })
      .on("contextmenu", (e, i) => {
        e.preventDefault();
        setMenuItems(contextMenuItems.moveDelete);
        contextMenu
          .attr("target", i) // gives context menu easy access to target peak/valley
          .attr("type", "valley")
          .style("position", "absolute")
          .style("left", e.layerX + 80 + "px") // layer does not take in scroll component so x and y stay within visible window
          .style("top", e.layerY + 50 + "px")
          .style("display", "block");
      })
      .call(d3.drag().on("start", dragStarted).on("drag", dragging).on("end", dragEnded));

    // bring dup markers to the top
    svg
      .selectAll("path#peak")
      .filter((d) => duplicateIndices.peaks.includes(d))
      .raise();
    svg
      .selectAll("path#valley")
      .filter((d) => duplicateIndices.valleys.includes(d))
      .raise();

    /* --------------------------------------
        PEAKS/VALLEYS THRESHOLD LINES
      -------------------------------------- */
    // ensure you can't move a line outside of window bounds
    function getCorrectY(newY) {
      return Math.min(Math.max(newY, y(yMax + yRange)), y(yMin - yRange));
    }

    const pivotLineDrag = d3
      .drag()
      .on("start", function () {
        // close context menu if it's open
        contextMenu.style("display", "none");
        // increase stroke width when selected and dragging
        d3.select(this).attr("stroke-width", 5);
      })
      .on("drag", function (d) {
        const yPosition = getCorrectY(d.y);

        // set new y for marker
        d3.select(this).attr("cy", yPosition);

        // set new y for line
        const id = d3.select(this).attr("id");
        const elementName = id.includes("peak") ? "#peakLine" : "#valleyLine";
        const yId = id.includes("1") ? "y1" : "y2";
        d3.select(elementName).attr(yId, yPosition);
      })
      .on("end", function (d) {
        // decrease stroke width when unselected and dropped
        d3.select(this).attr("stroke-width", 2);

        const id = d3.select(this).attr("id");

        const elementName = id.includes("peak") ? "#peakLine" : "#valleyLine";
        // need to invert to make calculation compatible with waveformForFeatures
        const yId = id.includes("1") ? "y1" : "y2";
        const newY = y.invert(d3.select(elementName).attr(yId));

        const featureName = id.includes("peak") ? "peaks" : "valleys";
        customAnalysisSettingsUpdaters.setThresholdEndpoints(featureName, { [yId]: newY });

        // decrease stroke width when unselected and dropped
        d3.select(this).attr("stroke-width", 2);
      });

    const moveLineUpDown = d3
      .drag()
      .on("start", function (d) {
        // close context menu if it's open
        contextMenu.style("display", "none");
        // increase stroke width when selected and dragging
        d3.select(this).attr("stroke-width", 5);
        // set y pos where the line was grabbed at
        d3.select(this).attr("prevGrabY", d.y);
      })
      .on("drag", function (d) {
        const id = d3.select(this).attr("id");
        // Get y value of line before the dragging happened
        const prevGrabY = d3.select(this).attr("prevGrabY");
        const changeInY = d.y - prevGrabY;

        const expectedNewY1 = parseFloat(d3.select(this).attr("y1")) + changeInY;
        const expectedNewY2 = parseFloat(d3.select(this).attr("y2")) + changeInY;
        const newY1 = getCorrectY(expectedNewY1);
        const newY2 = getCorrectY(expectedNewY2);

        // if these values don't match, then one of the endpoints of the lines went OOB and no updates should be performed
        if (newY1 === expectedNewY1 && newY2 === expectedNewY2) {
          const prefix = id.includes("peak") ? "peak" : "valley";
          d3.select(this).attr("y1", newY1);
          d3.select(this).attr("y2", newY2);
          d3.select(this).attr("prevGrabY", d.y);
          // set the y variables to prevent the lines from "floating" away from pointer
          d3.select(`#${prefix}LineY1Marker`).attr("cy", newY1);
          d3.select(`#${prefix}LineY2Marker`).attr("cy", newY2);
        }
      })
      .on("end", function () {
        const id = d3.select(this).attr("id");
        d3.select(this).attr("stroke-width", 2);
        const y1 = y.invert(d3.select(this).attr("y1"));
        const y2 = y.invert(d3.select(this).attr("y2"));

        const featureName = id.includes("peak") ? "peaks" : "valleys";
        customAnalysisSettingsUpdaters.setThresholdEndpoints(featureName, { y1, y2 });
      });

    // draggable windowed peaks line
    const peakThresholdLine = svg
      .append("line")
      .attr("id", "peakLine")
      .attr("x1", x(startTime))
      .attr("y1", y(thresholdEndpoints.peaks.y1))
      .attr("x2", x(endTime))
      .attr("y2", y(thresholdEndpoints.peaks.y2))
      .attr("stroke-width", 2)
      .attr("stroke", "var(--curi-peaks)")
      .style("cursor", "pointer")
      .call(moveLineUpDown);

    // this offset is used to shift the peak/valley threshold endpoint markers slightly inward so they
    // don't sit directly underneath window bound lines. The offset factor used here was chosen arbitrarily.
    // Could probably do this a better way
    const offsetFactor = 100;
    const endpointMarkerOffset = (endTime - startTime) / offsetFactor;

    const peaksY1 = appendFeatureMarkers(
      "peakLineY1Marker",
      "peakLine",
      startTime + endpointMarkerOffset,
      thresholdEndpoints.peaks.y1,
      "var(--curi-peaks)"
    );
    const peaksY2 = appendFeatureMarkers(
      "peakLineY2Marker",
      "peakLine",
      endTime - endpointMarkerOffset,
      thresholdEndpoints.peaks.y2,
      "var(--curi-peaks)"
    );
    // remove peaks line if no peaks are found
    if (!thresholdEndpoints.peaks.y1 || !thresholdEndpoints.peaks.y2) {
      peakThresholdLine.attr("display", "none");
      peaksY1.attr("display", "none");
      peaksY2.attr("display", "none");
    }
    // dragable windowed valleys line
    const valleyThresholdLine = svg
      .append("line")
      .attr("id", "valleyLine")
      .attr("x1", x(startTime))
      .attr("y1", y(thresholdEndpoints.valleys.y1))
      .attr("x2", x(endTime))
      .attr("y2", y(thresholdEndpoints.valleys.y2))
      .attr("stroke-width", 2)
      .attr("stroke", "var(--curi-valleys)")
      .style("cursor", "pointer")
      .call(moveLineUpDown);

    const valleysY1 = appendFeatureMarkers(
      "valleyLineY1Marker",
      "peakLine",
      startTime + endpointMarkerOffset,
      thresholdEndpoints.valleys.y1,
      "var(--curi-valleys)"
    );
    const valleysY2 = appendFeatureMarkers(
      "valleyLineY2Marker",
      "peakLine",
      endTime - endpointMarkerOffset,
      thresholdEndpoints.valleys.y2,
      "var(--curi-valleys)"
    );
    // remove valleys line if no valleys are found
    if (!thresholdEndpoints.valleys.y1 || !thresholdEndpoints.valleys.y2) {
      valleyThresholdLine.attr("display", "none");
      valleysY1.attr("display", "none");
      valleysY2.attr("display", "none");
    }

    /* --------------------------------------
        WINDOW START AND END TIME LINES
      -------------------------------------- */
    const timeLineDrag = d3
      .drag()
      .on("start", function () {
        // close context menu if it's open
        contextMenu.style("display", "none");
        // increase stroke width when selected and dragging
        d3.select(this).attr("stroke-width", 6);
      })
      .on("drag", function (d) {
        const time = d3.select(this).attr("id");
        const startingPos = startTimeLine.attr("x1");
        const endPos = endTimeLine.attr("x1");

        // ensure you can't move a line outside of window bounds
        let xPosition = Math.min(Math.max(d.x, 0), dynamicWidth);
        // ensure start time cannot go above end time and vice versa
        xPosition = time === "startTime" ? Math.min(xPosition, endPos) : Math.max(xPosition, startingPos);

        const attrName = time === "startTime" ? "x1" : "x2";
        // update peaks and valley windows to only be within the windowed analysis window
        peakThresholdLine.attr(attrName, xPosition);
        valleyThresholdLine.attr(attrName, xPosition);

        if (time === "startTime") {
          peaksY1.attr("cx", x(x.invert(xPosition) + endpointMarkerOffset));
          valleysY1.attr("cx", x(x.invert(xPosition) + endpointMarkerOffset));
        } else {
          peaksY2.attr("cx", x(x.invert(xPosition) - endpointMarkerOffset));
          valleysY2.attr("cx", x(x.invert(xPosition) - endpointMarkerOffset));
        }

        // assign new x values
        d3.select(this).attr("x1", xPosition).attr("x2", xPosition);

        // adjust rectangle fill to new adjusted width
        windowedAnalysisFill.attr("x", startingPos).attr("width", endPos - startingPos);
      })
      .on("end", function () {
        // save adjusted time to pass up to parent component to use across all wells
        // fix to two decimal places, otherwise GET /jobs/waveform-data will error
        const boundName = d3.select(this).attr("id") === "startTime" ? "start" : "end";
        const xPosition = d3.select(this).attr("x1");
        const newTimeSec = parseFloat(x.invert(xPosition).toFixed(2));

        customAnalysisSettingsUpdaters.setWindowBounds({ [boundName]: newTimeSec });
        // update peaks and valley windows to only be within the windowed analysis window
        const attrName = boundName === "start" ? "x1" : "x2";
        peakThresholdLine.attr(attrName, xPosition);
        valleyThresholdLine.attr(attrName, xPosition);

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
      .attr("y2", dynamicHeight)
      .attr("stroke-width", 5)
      .attr("stroke", "black")
      .style("cursor", "pointer")
      .call(timeLineDrag);
    // end of window analysis line
    const endTimeLine = svg
      .append("line")
      .attr("id", "endTime")
      .attr("x1", initialEndTime)
      .attr("y1", 0)
      .attr("x2", initialEndTime)
      .attr("y2", dynamicHeight)
      .attr("stroke-width", 5)
      .attr("stroke", "black")
      .style("cursor", "pointer")
      .call(timeLineDrag);

    /* --------------------------------------
        BLOCKERS (just top blocker for now)
      -------------------------------------- */
    svg
      .append("rect")
      .attr("x", -10)
      .attr("y", -margin.top)
      .attr("width", dynamicWidth + 15)
      .attr("height", margin.top)
      .attr("fill", "white")
      .style("overflow", "hidden");
  };

  const contextMenuClick = ({ target }) => {
    const contextMenu = d3.select("#contextmenu");
    const stringNode = contextMenu.attr("target");
    const targetIdx = parseFloat(stringNode);
    if (target.id === "Delete") {
      const featureType = contextMenu.attr("type");
      customAnalysisSettingsUpdaters.deleteFeature(`${featureType}s`, targetIdx);
    } else if (target.id === "Move") {
      const featureType = contextMenu.attr("type");

      const idxToChange = (featureType === "peak" ? peaks : valleys).indexOf(targetIdx);

      setSelectedMarkerToMove({
        type: featureType,
        idx: idxToChange,
      });
    } else {
      const featureType = target.id === "Add Peak" ? "peaks" : "valleys";
      customAnalysisSettingsUpdaters.addFeature(featureType, targetIdx);
    }
    contextMenu.style("display", "none");
  };

  const handleZoomIn = (axis) => {
    if (axis === "x") {
      const newFactor = xZoomFactor * 1.5;
      setXZoomFactor(newFactor);
    } else {
      const newFactor = yZoomFactor * 1.5;
      setYZoomFactor(newFactor);
    }
  };

  const handleZoomOut = (axis) => {
    // ensure max zoom out is initial render size because entire waveform will be in view, so there shouldn't be a need for it.
    if (axis === "x" && xZoomFactor != 1) {
      const newFactor = xZoomFactor / 1.5;
      setXZoomFactor(newFactor);
    } else if (yZoomFactor != 1) {
      const newFactor = yZoomFactor / 1.5;
      setYZoomFactor(newFactor);
    }
  };

  const getFeatureAlertMessage = () => {
    if (peaks.length === 0 && valleys.length === 0) return "No peaks or valleys detected";
    if (peaks.length === 0) return "No peaks detected";
    if (valleys.length === 0) return "No valleys detected";
    return "";
  };

  return (
    <>
      <YAxisContainer>
        <YAxisLabel>{yAxisLabel}</YAxisLabel>
        <ZoomWidget size={"20px"} zoomIn={() => handleZoomIn("y")} zoomOut={() => handleZoomOut("y")} />
      </YAxisContainer>
      <ColumnContainer>
        <ToolbarContainer>
          <NoFeaturesAlert>{getFeatureAlertMessage()}</NoFeaturesAlert>
          <ChangelogLabel onClick={changelogActions.open}>View Changelog</ChangelogLabel>
          <HowTo>
            Edit Peaks / Valleys{" "}
            <Tooltip
              title={
                <TooltipText>
                  <li>
                    Move:
                    <br />
                    Click and drag markers along the waveform line. Or right click to use arrow keys.
                  </li>
                  <li>
                    Add:
                    <br />
                    Right-click along waveform line for placemenet.
                  </li>
                  <li>
                    Delete:
                    <br />
                    Right-click directly on marker.
                  </li>
                  <li>
                    Window:
                    <br />
                    Drag orange and green horizontal lines to filter minimum peaks and maximum valleys.
                  </li>
                </TooltipText>
              }
            >
              <InfoOutlinedIcon sx={{ "&:hover": { color: "var(--teal-green)", cursor: "pointer" } }} />
            </Tooltip>
          </HowTo>
          <ButtonWidget
            label="Undo"
            width="80px"
            height="30px"
            fontSize={15}
            borderRadius="5px"
            clickFn={changelogActions.undo}
          />
          <ButtonWidget
            label="Reset"
            width="80px"
            height="30px"
            left="5px"
            fontSize={15}
            borderRadius="5px"
            clickFn={changelogActions.reset}
          />
          <ButtonWidget
            label="Save"
            width="80px"
            height="30px"
            left="10px"
            fontSize={15}
            borderRadius="5px"
            clickFn={changelogActions.save}
          />
        </ToolbarContainer>
        <Container id="scrollableContainer">
          <div id="waveformGraph" />
        </Container>
        <XAxisContainer>
          <Legend>
            <table>
              <tbody>
                <tr>
                  <td>
                    <Triangle type="peak" direction="top" />
                    Peaks
                  </td>
                  <td>
                    <LineColor type="peak" />
                    Peak Detection Limit
                  </td>
                  <td>
                    <LineAdjuster type="peak" />
                    Peak Limit Adjuster
                  </td>
                  <td>
                    <Triangle type="valley" direction="bottom" />
                    Valleys
                  </td>
                  <td>
                    <LineColor type="valley" />
                    Valley Limiter
                  </td>
                  <td>
                    <LineAdjuster type="valley" />
                    Valley Limit Adjuster
                  </td>
                  <td>
                    <ToRowComponent>
                      <Triangle type="error" direction="top" />
                      <Triangle type="error" direction="bottom" />
                    </ToRowComponent>
                    Duplicate Valley or Peak
                  </td>
                </tr>
              </tbody>
            </table>
          </Legend>
          <ToRowComponent>
            <XAxisLabel>Time (seconds)</XAxisLabel>
            <ZoomWidget size={"20px"} zoomIn={() => handleZoomIn("x")} zoomOut={() => handleZoomOut("x")} />
          </ToRowComponent>
          <CursorLocLabel>
            Cursor: [ {cursorLoc[0]}, {cursorLoc[1]} ]
          </CursorLocLabel>
        </XAxisContainer>
      </ColumnContainer>
      <ContextMenuContainer id="contextmenu">
        {menuItems.map((item) => {
          return (
            <MenuItem id={item} key={item} onClick={contextMenuClick}>
              {item}
            </MenuItem>
          );
        })}
      </ContextMenuContainer>
    </>
  );
}
