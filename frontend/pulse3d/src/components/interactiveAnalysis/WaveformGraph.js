import styled from "styled-components";
import { useEffect, useState } from "react";
import * as d3 from "d3";
import ZoomWidget from "../basicWidgets/ZoomWidget";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";
import MenuItem from "@mui/material/MenuItem";
import ButtonWidget from "../basicWidgets/ButtonWidget";

const Container = styled.div`
  width: 1260px;
  height: 320px;
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
  position: absolute;
  left: 1100px;
  cursor: default;
`;

const TooltipText = styled.span`
  font-size: 15px;
`;

const ColumnContainer = styled.div`
  bottom: 25px;
  position: relative;
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
  top: 44%;
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

const contextMenuItems = {
  moveDelete: ["Move", "Delete"],
  add: ["Add Peak", "Add Valley"],
};

export default function WaveformGraph({
  dataToGraph,
  initialPeaksValleys,
  startTime,
  endTime,
  setEditableStartEndTimes,
  editablePeaksValleys,
  currentWell,
  setEditablePeaksValleys,
  xRange,
  resetWellChanges,
  saveChanges,
  deletePeakValley,
  addPeakValley,
  openChangelog,
  undoLastChange,
  minPeakLine,
  maxValleyLine,
  peakValleyWindows,
  setPeakValleyWindows,
}) {
  const [valleys, setValleys] = useState([]);
  const [peaks, setPeaks] = useState([]);
  const [newStartTime, setNewStartTime] = useState(xRange.min);
  const [newEndTime, setNewEndTime] = useState(xRange.max);
  const [menuItems, setMenuItems] = useState(contextMenuItems.moveDelete);
  const [selectedMarkerToMove, setSelectedMarkerToMove] = useState();
  const [cursorLoc, setCursorLoc] = useState([0, 0]);
  const [xZoomFactor, setXZoomFactor] = useState(1);
  const [yZoomFactor, setYZoomFactor] = useState(1);
  /* NOTE!! The order of the variables and functions in createGraph() are important to functionality.
     could eventually try to break this up, but it's more sensitive in react than vue */
  const createGraph = () => {
    /* --------------------------------------
      SET UP SVG GRAPH AND VARIABLES
    -------------------------------------- */
    const maxTime = d3.max(dataToGraph, (d) => {
      return d[0];
    });

    // if windowed analysis, use else use recording max and min times
    const xMin = xRange.min ? xRange.min : dataToGraph[0][0];
    const xMax = xRange.max ? xRange.max : maxTime;

    const margin = { top: 20, right: 20, bottom: 30, left: 50 },
      width = 1245 - margin.left - margin.right,
      height = 300 - margin.top - margin.bottom;

    // TODO handle if zoom becomes smaller than smallest component width
    const dynamicWidth = width * xZoomFactor < width ? width : width * xZoomFactor;
    const dynamicHeight = height * yZoomFactor < height ? height : height * yZoomFactor;
    // Add X axis and Y axis
    const x = d3.scaleLinear().range([0, dynamicWidth]).domain([xMin, xMax]);

    // add .15 extra to y max and y min to auto scale the graph a little outside of true max and mins
    const yMax = d3.max(dataToGraph, (d) => d[1]);
    const yMin = d3.min(dataToGraph, (d) => d[1]);
    const yRange = yMax * 0.15;

    const y = d3
      .scaleLinear()
      .range([dynamicHeight, 0])
      .domain([yMin - yRange, yMax + yRange]);
    // calculate start and end times in pixels. If windowed time found, use, else recording max and min
    const initialStartTime = x(startTime ? startTime : xMin);
    const initialEndTime = x(endTime ? endTime : maxTime);

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
        movePeakValley(e.keyCode);
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
      const coords =
        selectedMarkerToMove.type === "peak"
          ? dataToGraph[peaks[selectedMarkerToMove.idx]]
          : dataToGraph[valleys[selectedMarkerToMove.idx]];

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

            // reposition start time, peaks, valleys lines and set value to state
            startTimeLine.attr("x1", position).attr("x2", position);
            valleysWindowLine.attr("x1", position);
            peaksWindowLine.attr("x1", position);

            // reposition end time, peaks, valleys lines and set value to state
            const endPosition = parseFloat(position) + parseFloat(timeWidth);
            endTimeLine.attr("x1", endPosition).attr("x2", endPosition);
            valleysWindowLine.attr("x2", endPosition);
            peaksWindowLine.attr("x2", endPosition);
          })
          .on("end", function () {
            const timeWidth = d3.select(this).attr("width");
            const startPosition = d3.select(this).attr("x");
            const endPosition = parseFloat(startPosition) + parseFloat(timeWidth);
            // save new window analysis times to state on end so that it only updates changelog on drop
            setNewStartTime(x.invert(startPosition));
            setNewEndTime(x.invert(endPosition));

            d3.select(this).attr("opacity", 0.2).attr("cursor", "default");
          })
      );

    /* --------------------------------------
      WAVEFORM TISSUE LINE
    -------------------------------------- */
    svg
      .append("path")
      .data([
        dataToGraph
          .filter((coord) => coord[0] <= xMax && coord[0] >= xMin)
          .map((x) => [x[0] * xZoomFactor, x[1] * yZoomFactor]),
      ])
      .attr("fill", "none")
      .attr("stroke", "steelblue")
      .attr("stroke-width", 2)
      .attr("d", dataLine)
      .on("contextmenu", (e) => {
        e.preventDefault();
        setMenuItems(contextMenuItems.add);
        contextMenu
          .attr("target", x.invert(e.offsetX - 50)) // gives context menu easy access to target peak/valley
          .style("position", "absolute")
          .style("left", e.layerX + 80 + "px") // layer does not take in scroll component so x and y stay within visible window
          .style("top", e.layerY + 50 + "px")
          .style("display", "block");
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
      const peakOrValley = d3.select(this).attr("id");

      // sets static cursor coordinates to empty because marker already has coordinates when dragging
      setCursorLoc(["_ ", "_"]);
      // invert gives the location of the mouse based on the x and y domains
      d[0] = x.invert(d.x);
      d[1] = y.invert(d.y);

      /*
        To force circle to stay along data line, find index of x-coordinate in datapoints to then grab corresponding y-coordinate
        If this is skipped, user will be able to drag circle anywhere on graph, unrelated to data line.
      */
      const draggedIdx = dataToGraph.findIndex((x) => Number(x[0].toFixed(2)) === Number(d[0].toFixed(2)));

      // assigns circle node new x and y coordinates based off drag event
      if (peakOrValley === "peak") {
        d3.select(this).attr(
          "transform",
          "translate(" + x(d[0]) + "," + (y(dataToGraph[draggedIdx][1]) - 7) + ") rotate(180)"
        );
      } else {
        d3.select(this).attr(
          "transform",
          "translate(" + x(d[0]) + "," + (y(dataToGraph[draggedIdx][1]) + 7) + ")"
        );
      }

      // update the focus text with current x and y data points as user drags marker
      focusText
        .html("[ " + d[0].toFixed(2) + ", " + dataToGraph[draggedIdx][1].toFixed(2) + " ]")
        .attr("x", x(d[0]) + 15)
        .attr("y", y(dataToGraph[draggedIdx][1]) - 20)
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
        (coords) => Number(coords[0].toFixed(2)) === Number(x.invert(d.x).toFixed(2))
      );

      // Changing the x/y coordinates on the graph does not auto update the original array used to plot peaks and valleys so you need to update them separately
      if (peakOrValley === "peak") {
        peaks.splice(indexToChange, 1, newSelectedIndex);
        setPeaks([...peaks]); // required to change dependencies
      } else {
        valleys.splice(indexToChange, 1, newSelectedIndex);
        setValleys([...valleys]); // required to change dependencies
      }
    }
    // graph all the peak markers
    svg
      .selectAll("#waveformGraph")
      .data(
        initialPeaksValleys[0].filter((peak) => {
          return (
            dataToGraph[peak][0] >= startTime &&
            dataToGraph[peak][0] <= endTime &&
            dataToGraph[peak][1] >= peakValleyWindows[currentWell].minPeaks
          );
        })
      )
      .enter()
      .append("path")
      .attr("id", "peak")
      .attr("indexToReplace", (d) => initialPeaksValleys[0].indexOf(d)) // keep track of index in peaks array to splice later
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", (d) => {
        return "translate(" + x(dataToGraph[d][0]) + "," + (y(dataToGraph[d][1]) - 7) + ") rotate(180)";
      })
      .style("fill", "orange")
      .attr("stroke", "orange")
      .style("cursor", "pointer")
      .style("display", (d) => {
        // only display them inside windowed analysis times
        const xTime = dataToGraph[d][0];
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
      .data(
        initialPeaksValleys[1].filter((valley) => {
          return (
            dataToGraph[valley][0] >= startTime &&
            dataToGraph[valley][0] <= endTime &&
            dataToGraph[valley][1] <= peakValleyWindows[currentWell].maxValleys
          );
        })
      )
      .enter()
      .append("path")
      .attr("id", "valley")
      .attr("indexToReplace", (d) => initialPeaksValleys[1].indexOf(d)) // keep track of index in valleys array to splice later
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", (d) => {
        return "translate(" + x(dataToGraph[d][0]) + "," + (y(dataToGraph[d][1]) + 7) + ")";
      })
      .style("fill", "green")
      .attr("stroke", "green")
      .style("cursor", "pointer")
      .style("display", (d) => {
        // only display them inside windowed analysis times
        const xTime = dataToGraph[d][0];
        return xTime > xMax || xTime < xMin ? "none" : null;
      })
      .call(d3.drag().on("start", dragStarted).on("drag", dragging).on("end", dragEnded))
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
      });

    /* --------------------------------------
      WINDOWED PEAKS/VALLEYS LINES
    -------------------------------------- */
    const peaksValleysLineDrag = d3
      .drag()
      .on("start", function () {
        // close context menu if it's open
        contextMenu.style("display", "none");
        // increase stroke width when selected and dragging
        d3.select(this).attr("stroke-width", 5);
      })
      .on("drag", function (d) {
        const id = d3.select(this).attr("id");
        const peakLinePos = peaksWindowLine.attr("y1");
        const valleyLinePos = valleysWindowLine.attr("y1");

        let yPosition;
        if (id == "peakLine") {
          // ensure you can't move a line outside of window bounds
          yPosition = d.y >= valleyLinePos ? valleyLinePos : d.y < y(yMax + yRange) ? y(yMax + yRange) : d.y;
        } else {
          yPosition = d.y <= peakLinePos ? peakLinePos : d.y > y(yMin - yRange) ? y(yMin - yRange) : d.y;
        }

        // assign new x values
        d3.select(this).attr("y1", yPosition).attr("y2", yPosition);
      })
      .on("end", function () {
        const id = d3.select(this).attr("id");
        const yPosition = d3.select(this).attr("y1");

        d3.select(this).attr("y1", yPosition).attr("y2", yPosition);

        const pvCopy = peakValleyWindows;
        if (id === "peakLine") {
          pvCopy[currentWell].minPeaks = y.invert(yPosition);
          setPeakValleyWindows({ ...pvCopy });
        } else {
          pvCopy[currentWell].maxValleys = y.invert(yPosition);
          setPeakValleyWindows({ ...pvCopy });
        }
        // descrease stroke width when unselected and dropped
        d3.select(this).attr("stroke-width", 2);
      });

    // draggable windowed peaks line
    const peaksWindowLine = svg
      .append("line")
      .attr("id", "peakLine")
      .attr("x1", x(startTime))
      .attr("y1", y(peakValleyWindows[currentWell].minPeaks))
      .attr("x2", x(endTime))
      .attr("y2", y(peakValleyWindows[currentWell].minPeaks))
      .attr("stroke-width", 2)
      .attr("stroke", "orange")
      .style("cursor", "pointer")
      .call(peaksValleysLineDrag);
    // dragable windowed valleys line
    const valleysWindowLine = svg
      .append("line")
      .attr("id", "valleyLine")
      .attr("x1", x(startTime))
      .attr("y1", y(peakValleyWindows[currentWell].maxValleys))
      .attr("x2", x(endTime))
      .attr("y2", y(peakValleyWindows[currentWell].maxValleys))
      .attr("stroke-width", 2)
      .attr("stroke", "green")
      .style("cursor", "pointer")
      .call(peaksValleysLineDrag);

    /* --------------------------------------
      START AND END TIME LINES
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
        let xPosition = d.x < 0 ? 0 : d.x > dynamicWidth ? dynamicWidth : d.x;

        // ensure start time cannot go above end time and vice versa
        if (time === "startTime") {
          if (d.x >= endPos) xPosition = endPos;
          // update peaks and valley windows to only be within the windowed analysis window
          peaksWindowLine.attr("x1", xPosition);
          valleysWindowLine.attr("x1", xPosition);
        } else if (time === "endTime") {
          if (d.x <= startingPos) xPosition = startingPos;
          // update peaks and valley windows to only be within the windowed analysis window
          peaksWindowLine.attr("x2", xPosition);
          valleysWindowLine.attr("x2", xPosition);
        }

        // assign new x values
        d3.select(this).attr("x1", xPosition).attr("x2", xPosition);

        // adjust rectangle fill to new adjusted width
        windowedAnalysisFill.attr("x", startingPos).attr("width", endPos - startingPos);
      })
      .on("end", function () {
        // save adjusted time to pass up to parent component to use across all wells
        // fix to two decimal places, otherwise GET /jobs/waveform_data will error
        const time = d3.select(this).attr("id");
        const xPosition = d3.select(this).attr("x1");
        const newTimeSec = parseFloat(x.invert(xPosition).toFixed(2));

        if (time === "startTime") {
          setNewStartTime(newTimeSec);
          // update peaks and valley windows to only be within the windowed analysis window
          peaksWindowLine.attr("x1", xPosition);
          valleysWindowLine.attr("x1", xPosition);
        } else {
          setNewEndTime(newTimeSec);
          // update peaks and valley windows to only be within the windowed analysis window
          peaksWindowLine.attr("x2", xPosition);
          valleysWindowLine.attr("x2", xPosition);
        }

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

  useEffect(() => {
    if (initialPeaksValleys.length > 0) {
      // always remove existing graph before plotting new graph
      d3.select("#waveformGraph").select("svg").remove();
      /*
        TODO!! this is bad form to directly mutate state,
        but so far is the only way it will render the new peaks and valleys
        when selecting between wells in dropdown
      */
      peaks.splice(0, peaks.length);
      initialPeaksValleys[0].map((x) => peaks.push(x));

      valleys.splice(0, valleys.length);
      initialPeaksValleys[1].map((x) => valleys.push(x));

      setNewStartTime(startTime);
      setNewEndTime(endTime);
      createGraph();
    }
  }, [
    initialPeaksValleys,
    selectedMarkerToMove,
    xZoomFactor,
    yZoomFactor,
    startTime,
    endTime,
    peakValleyWindows,
  ]);

  useEffect(() => {
    // manually scrolls graph div to bottom because the graph div expands down instead of up
    const containerToScroll = document.getElementById("scrollableContainer");
    containerToScroll.scrollTop = containerToScroll.scrollHeight;
  }, [yZoomFactor]);

  useEffect(() => {
    // sometimes this does get updated to null when moving windowed analysis fill
    // so need to update to max or min if so to prevent changelog message from erroring
    setEditableStartEndTimes({
      startTime: newStartTime ? newStartTime : xRange.min,
      endTime: newEndTime ? newEndTime : xRange.max,
    });
  }, [newStartTime, newEndTime]);

  useEffect(() => {
    // ensures you don't edit the original array by creating deep copy
    const newEntries = JSON.parse(JSON.stringify(editablePeaksValleys));
    newEntries[currentWell] = [[...peaks], [...valleys]];
    setEditablePeaksValleys(newEntries);
  }, [peaks, valleys]);

  const filterPeaksValleys = () => {};

  const contextMenuClick = ({ target }) => {
    const contextMenu = d3.select("#contextmenu");
    const stringNode = contextMenu.attr("target");
    const targetIdx = parseFloat(stringNode);

    if (target.id === "Delete") {
      const peakValley = contextMenu.attr("type");
      deletePeakValley(peakValley, targetIdx);
    } else if (target.id === "Move") {
      const peakValley = contextMenu.attr("type");

      const idxToChange = peakValley === "peak" ? peaks.indexOf(targetIdx) : valleys.indexOf(targetIdx);

      setSelectedMarkerToMove({
        type: peakValley,
        idx: idxToChange,
      });
    } else {
      const peakValley = target.id === "Add Peak" ? "peak" : "valley";
      addPeakValley(peakValley, targetIdx);
    }
    contextMenu.style("display", "none");
  };

  const movePeakValley = (keyCode) => {
    const { type, idx } = selectedMarkerToMove;

    if (keyCode === 37) {
      // 37 is left arrow key
      if (type === "peak") {
        const idxVal = peaks[idx];
        peaks.splice(idx, 1, (idxVal -= 1));
        setPeaks([...peaks]); // required to change dependencies
      } else {
        const idxVal = valleys[idx];
        valleys.splice(idx, 1, (idxVal -= 1));
        setValleys([...valleys]); // required to change dependencies
      }
    } else if (keyCode === 39) {
      // 39 is right arrow key
      if (type === "peak") {
        const idxVal = peaks[idx];
        peaks.splice(idx, 1, (idxVal += 1));
        setPeaks([...peaks]); // required to change dependencies
      } else {
        const idxVal = valleys[idx];
        valleys.splice(idx, 1, (idxVal += 1));
        setValleys([...valleys]); // required to change dependencies
      }
    }
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

  return (
    <>
      <YAxisContainer>
        <YAxisLabel>Active Twitch Force (uN)</YAxisLabel>
        <ZoomWidget size={"20px"} zoomIn={() => handleZoomIn("y")} zoomOut={() => handleZoomOut("y")} />
      </YAxisContainer>
      <ColumnContainer>
        <ToolbarContainer>
          <ChangelogLabel onClick={openChangelog}>View Changelog</ChangelogLabel>
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
            clickFn={undoLastChange}
          />
          <ButtonWidget
            label="Reset"
            width="80px"
            height="30px"
            left="5px"
            fontSize={15}
            borderRadius="5px"
            clickFn={resetWellChanges}
          />
          <ButtonWidget
            label="Save"
            width="80px"
            height="30px"
            left="10px"
            fontSize={15}
            borderRadius="5px"
            clickFn={saveChanges}
          />
        </ToolbarContainer>
        <Container id="scrollableContainer">
          <div id="waveformGraph" />
        </Container>
        <XAxisContainer>
          <XAxisLabel>Time (seconds)</XAxisLabel>
          <ZoomWidget size={"20px"} zoomIn={() => handleZoomIn("x")} zoomOut={() => handleZoomOut("x")} />

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
