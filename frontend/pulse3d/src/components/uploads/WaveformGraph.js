import styled from "styled-components";
import { useEffect, useState } from "react";
import * as d3 from "d3";
// import ZoomWidget from "../basicWidgets/ZoomWidget";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import Tooltip from "@mui/material/Tooltip";
import MenuItem from "@mui/material/MenuItem";
import ButtonWidget from "../basicWidgets/ButtonWidget";

const Container = styled.div`
  width: 1270px;
  height: 320px;
  background-color: white;
  overflow-x: scroll;
  overflow-y: hidden;
  position: relative;
  left: 50px;
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

const TooltipText = styled.span`
  font-size: 15px;
`;

const ColumnContainer = styled.div`
  bottom: 15px;
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
`;

const ContextMenuContainer = styled.div`
  font-size: 16px;
  background-color: white;
  display: none;
  border-radius: 6px;
  box-shadow: 0px 5px 5px -3px rgb(0 0 0 / 30%),
    0px 8px 10px 1px rgb(0 0 0 / 20%), 0px 3px 14px 2px rgb(0 0 0 / 12%);
`;

const contextMenuItems = {
  delete: ["Delete"],
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
}) {
  const [valleys, setValleys] = useState([]);
  const [peaks, setPeaks] = useState([]);
  const [newStartTime, setNewStartTime] = useState();
  const [newEndTime, setNewEndTime] = useState();
  const [menuItems, setMenuItems] = useState(contextMenuItems.delete);

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
    const lengthOfRecording = xMax - xMin;

    const margin = { top: 20, right: 20, bottom: 30, left: 50 },
      width = 1270 - margin.left - margin.right,
      height = 300 - margin.top - margin.bottom;

    // currently sets 10 secs inside the graph window and multiples width to fit length of recording
    const widthMultiple =
      lengthOfRecording / 10 < 1 ? 1 : lengthOfRecording / 10;
    const dynamicWidth = width * widthMultiple;

    // Add X axis and Y axis
    const x = d3.scaleLinear().range([0, dynamicWidth]).domain([xMin, xMax]);

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

    // calculate start and end times in pixels. If windowed time found, use, else recording max and min
    const initialStartTime = x(startTime ? startTime : xMin);
    const initialEndTime = x(endTime ? endTime : xMax);

    // waveform line
    const dataLine = d3
      .line()
      .x((d) => {
        return x(d[0]);
      })
      .y((d) => {
        return y(d[1]);
      });

    // setup custom  context menu
    const contextMenu = d3.select("#contextmenu");

    // append the svg object to the body of the page
    const svg = d3
      .select("#waveformGraph")
      .append("svg")
      .attr("width", dynamicWidth + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .on("mousedown", () => {
        contextMenu.style("display", "none");
      })
      .on("contextmenu", (e) => {
        e.preventDefault();
        // setMenuItems(contextMenuItems.add);
        // contextMenu
        //   .attr("target", x.invert(e.offsetX - 50)) // gives context menu easy access to target peak/valley
        //   .style("position", "absolute")
        //   .style("left", e.layerX + 80 + "px") // layer does not take in scroll component so x and y stay within visible window
        //   .style("top", e.layerY + 50 + "px")
        //   .style("display", "block");
      })
      .append("g")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    // Create the text that travels along the curve of chart
    const focusText = svg
      .append("g")
      .append("text")
      .style("opacity", 0)
      .attr("text-anchor", "left")
      .attr("alignment-baseline", "middle");

    /* --------------------------------------
      APPEND X AND Y AXES
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
            // close context menu if it's open
            contextMenu.style("display", "none");

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

            // reposition start time line and set value to state
            startTimeLine.attr("x1", position).attr("x2", position);
            setNewStartTime(x.invert(position));

            // reposition end time line and set value to state
            const endPosition = position + parseFloat(timeWidth);
            endTimeLine.attr("x1", endPosition).attr("x2", endPosition);
            setNewEndTime(x.invert(endPosition));
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
      .data([
        dataToGraph.filter((coord) => coord[0] <= xMax && coord[0] >= xMin),
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

      // invert gives the location of the mouse based on the x and y domains
      d[0] = x.invert(d.x);
      d[1] = y.invert(d.y);

      /* 
        To force circle to stay along data line, find index of x-coordinate in datapoints to then grab corresponding y-coordinate 
        If this is skipped, user will be able to drag circle anywhere on graph, unrelated to data line.
      */
      const draggedIdx = dataToGraph.findIndex(
        (x) => Number(x[0].toFixed(2)) === Number(d[0].toFixed(2))
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
        (coords) =>
          Number(coords[0].toFixed(2)) === Number(x.invert(d.x).toFixed(2))
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
      .data(initialPeaksValleys[0])
      .enter()
      .append("path")
      .attr("id", "peak")
      .attr("indexToReplace", (d) => initialPeaksValleys[0].indexOf(d)) // keep track of index in peaks array to splice later
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", (d) => {
        return (
          "translate(" +
          x(dataToGraph[d][0]) +
          "," +
          (y(dataToGraph[d][1]) - 7) +
          ") rotate(180)"
        );
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
        setMenuItems(contextMenuItems.delete);
        contextMenu
          .attr("target", i) // gives context menu easy access to target peak/valley
          .attr("type", "peak")
          .style("position", "absolute")
          .style("left", e.layerX + 80 + "px") // layer does not take in scroll component so x and y stay within visible window
          .style("top", e.layerY + 50 + "px")
          .style("display", "block");
      })
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
      .attr("id", "valley")
      .attr("indexToReplace", (d) => initialPeaksValleys[1].indexOf(d)) // keep track of index in valleys array to splice later
      .attr("d", d3.symbol().type(d3.symbolTriangle).size(50))
      .attr("transform", (d) => {
        return (
          "translate(" +
          x(dataToGraph[d][0]) +
          "," +
          (y(dataToGraph[d][1]) + 7) +
          ")"
        );
      })
      .style("fill", "green")
      .attr("stroke", "green")
      .style("cursor", "pointer")
      .style("display", (d) => {
        // only display them inside windowed analysis times
        const xTime = dataToGraph[d][0];
        return xTime > xMax || xTime < xMin ? "none" : null;
      })
      .call(
        d3
          .drag()
          .on("start", dragStarted)
          .on("drag", dragging)
          .on("end", dragEnded)
      )
      .on("contextmenu", (e, i) => {
        e.preventDefault();
        setMenuItems(contextMenuItems.delete);
        contextMenu
          .attr("target", i) // gives context menu easy access to target peak/valley
          .attr("type", "valley")
          .style("position", "absolute")
          .style("left", e.layerX + 80 + "px") // layer does not take in scroll component so x and y stay within visible window
          .style("top", e.layerY + 50 + "px")
          .style("display", "block");
      });

    /* --------------------------------------
      START AND END TIME LINES
    -------------------------------------- */
    const lineDrag = d3
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
        if (time === "startTime" && d.x >= endPos) {
          xPosition = endPos;
        } else if (time === "endTime" && d.x <= startingPos) {
          xPosition = startingPos;
        }

        // assign new x values
        d3.select(this).attr("x1", xPosition).attr("x2", xPosition);

        // save adjusted time to pass up to parent component to use across all wells
        // fix to two decimal places, otherwise GET /jobs/waveform_data will error
        const newTimeSec = parseFloat(x.invert(xPosition).toFixed(2));
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
  }, [initialPeaksValleys]);

  useEffect(() => {
    setEditableStartEndTimes({
      startTime: newStartTime,
      endTime: newEndTime,
    });
  }, [newStartTime, newEndTime]);

  useEffect(() => {
    // ensures you don't edit the original array by creating deep copy
    const newEntries = JSON.parse(JSON.stringify(editablePeaksValleys));
    newEntries[currentWell] = [[...peaks], [...valleys]];
    setEditablePeaksValleys(newEntries);
  }, [peaks, valleys]);

  const contextMenuClick = ({ target }) => {
    const contextMenu = d3.select("#contextmenu");

    if (target.id === "Delete") {
      const peakValleyIndex = contextMenu.attr("target");
      const peakValley = contextMenu.attr("type");
      deletePeakValley(peakValley, peakValleyIndex);
    } else {
      const targetTime = contextMenu.attr("target");
      const peakValley = target.id === "Add Peak" ? "peak" : "valley";
      addPeakValley(peakValley, targetTime);
    }
    contextMenu.style("display", "none");
  };

  return (
    <>
      <YAxisContainer>
        <YAxisLabel>Active Twitch Force (uN)</YAxisLabel>
        {/* <ZoomWidget size={"20px"} /> */}
      </YAxisContainer>
      <ColumnContainer>
        <ToolbarContainer>
          <HowTo>
            Edit Peaks / Valleys{" "}
            <Tooltip
              title={
                <TooltipText>
                  <li>
                    Move:
                    <br />
                    Click and drag markers along the waveform line.
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
                </TooltipText>
              }
            >
              <InfoOutlinedIcon />
            </Tooltip>
          </HowTo>
          <ButtonWidget
            label="Reset"
            width="80px"
            height="30px"
            fontSize={15}
            borderRadius="5px"
            clickFn={resetWellChanges}
          />
          <ButtonWidget
            label="Save"
            width="80px"
            height="30px"
            left="5px"
            fontSize={15}
            borderRadius="5px"
            clickFn={saveChanges}
          />
        </ToolbarContainer>
        <Container>
          <div id="waveformGraph" />
        </Container>
        <XAxisContainer>
          <XAxisLabel>Time (seconds)</XAxisLabel>
          {/* <ZoomWidget size={"20px"} /> */}
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
