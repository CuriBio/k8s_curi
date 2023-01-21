import { useEffect, useState } from "react";
import CircularProgressWithLabel from "./CircularProgressWithLabel";
import { useContext } from "react";
import { AuthContext } from "@/pages/_app";
export default function UsageProgressWidget() {
  const { usageQuota } = useContext(AuthContext);
  const [maxUploads, setMaxUploads] = useState(-1);
  const [actualUploads, setActualUploads] = useState(0);
  useEffect(() => {
    console.log(usageQuota);
    if (usageQuota) {
      setMaxUploads(parseInt(usageQuota.limits.jobs));
      setActualUploads(parseInt(usageQuota.current.jobs));
    }
  }, [usageQuota]);
  return (
    <>
      {maxUploads === -1 ? (
        <div>Unlimited Access</div>
      ) : (
        <>
          <div id="progress">
            <p>Usage</p>
            <CircularProgressWithLabel value={parseInt((actualUploads / maxUploads) * 100)} />
            <p id="display">{`${actualUploads}/${maxUploads} Analysis used`}</p>
          </div>
        </>
      )}
      <style jsx>{`
        div#progress {
          color: white;
          display: flex;
          justify-content: space-around;
          align-items: center;
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
