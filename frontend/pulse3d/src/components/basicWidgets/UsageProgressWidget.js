import { useEffect, useState } from "react";
import CircularProgressWithLabel from "./CircularProgressWithLabel";
import { useContext } from "react";
import { AuthContext } from "@/pages/_app";
export default function UsageProgressWidget({ labelColor }) {
  const { usageQuota } = useContext(AuthContext);
  const [maxUploads, setMaxUploads] = useState(-1);
  const [actualUploads, setActualUploads] = useState(0);
  const [UsagePercentage, setUsagePercentage] = useState(0);

  //update usage data
  useEffect(() => {
    console.log(usageQuota);
    if (usageQuota) {
      const limit = parseInt(usageQuota.limits.jobs);
      const actual = parseInt(usageQuota.current.jobs);
      setMaxUploads(limit);
      setActualUploads(actual);
      const UsagePercentage = parseInt((actual / limit) * 100);
      if (UsagePercentage > 100) {
        setUsagePercentage(100);
      } else {
        setUsagePercentage(UsagePercentage);
      }
    }
  }, [usageQuota]);

  return (
    <>
      {maxUploads === -1 ? (
        <div id="progress">Unlimited Access</div>
      ) : (
        <>
          <div id="progress">
            <p>Usage</p>
            <CircularProgressWithLabel value={UsagePercentage} labelColor={labelColor} />
            <p id="display">{`${actualUploads}/${maxUploads} Analysis used`}</p>
          </div>
        </>
      )}
      <style jsx>{`
        div#progress {
          color: white;
          display: flex;
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
