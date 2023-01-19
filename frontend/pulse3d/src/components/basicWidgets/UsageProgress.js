import { useState } from "react";
import CircularProgressWithLabel from "./CircularProgressWithLabel";

export default function UsageProgress() {
  const [maxUploads, setMaxUploads] = useState(600);
  const [actualUploads, setActualUploads] = useState(333);
  return (
    <>
      <div id="container">
        <p>Usage</p>
        <div id="progress">
          <CircularProgressWithLabel value={parseInt((actualUploads / maxUploads) * 100)} />
          <p id="display">{`${actualUploads}/${maxUploads} uploads used`}</p>
        </div>
      </div>
      <style jsx>{`
        div#container {
          color: white;
          display: flex;
          align-items: center;
        }
        div#progress {
          display: flex;
          justify-content: space-around;
          column-count: 1;
          column-gap: 10px;
        }
        p#display {
          font-size: 0.85rem;
        }
      `}</style>
    </>
  );
}
