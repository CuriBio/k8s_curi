import { useEffect, useState } from "react";
import CircularProgressWithLabel from "./CircularProgressWithLabel";
import { useContext } from "react";
import { AuthContext } from "@/pages/_app";
export default function UsageProgressWidget({ labeltextcolor }) {
  const { usageQuota } = useContext(AuthContext);
  const [maxUploads, setMaxUploads] = useState(-1);
  const [actualUploads, setActualUploads] = useState(0);
  const [UsagePercentage, setUsagePercentage] = useState(0);

  useEffect(() => {
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

  const component = () => {
    let usageState;
    if (maxUploads === -1) {
      // Unlimited mode
      usageState = (
        <>
          <div id="progress">Unlimited Access</div>
          <style jsx>{`
            div#progress {
              color: white;
              display: flex;
              align-items: center;
              column-count: 1;
              column-gap: 10px;
            }
          `}</style>
        </>
      );
    } else if (!usageQuota.jobs_reached) {
      // max usage has not been reached
      usageState = (
        <>
          <div id="progress">
            <p>Usage</p>
            <CircularProgressWithLabel value={UsagePercentage} labeltextcolor={labeltextcolor} />
            <p id="display">{`${actualUploads}/${maxUploads} Analysis used`}</p>
          </div>
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
    } else {
      // not unlimited account and
      // usage max is reached and
      // plan has expired
      usageState = (
        <>
          <p id="expired">Plan Has Expired</p>
          <style jsx>{`
            p#expired {
              color: white;
            }
          `}</style>
        </>
      );
    }
    return usageState;
  };

  return <>{component()}</>;
}
