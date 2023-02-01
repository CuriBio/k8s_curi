import { useEffect, useState } from "react";
import CircularProgressWithLabel from "./CircularProgressWithLabel";
import { useContext } from "react";
import { AuthContext } from "@/pages/_app";
import styled from "styled-components";

const ProgressDiv = styled.div`
  color: white;
  display: flex;
  align-items: center;
  column-count: 1;
  column-gap: 10px;
`;
const ProgressP = styled.p`
  font-size: 0.85rem;
`;
const ExpiredP = styled.p`
  color: white;
`;

export default function UsageProgressWidget({ colorOfTextLabel }) {
  const { usageQuota } = useContext(AuthContext);
  const [maxUploads, setMaxUploads] = useState(-1);
  const [actualUploads, setActualUploads] = useState(0);
  const [usagePercentage, setUsagePercentage] = useState(0);

  useEffect(() => {
    if (usageQuota && usageQuota.limits && usageQuota.current) {
      const limit = parseInt(usageQuota.limits.jobs);
      const actual = parseInt(usageQuota.current.jobs);
      setMaxUploads(limit);
      setActualUploads(actual);
      const usagePercentage = parseInt((actual / limit) * 100);
      if (usagePercentage > 100) {
        setUsagePercentage(100);
      } else {
        setUsagePercentage(usagePercentage);
      }
    }
  }, [usageQuota]);

  const CorrectCardComponent = () => {
    let usageState;
    if (maxUploads === -1) {
      // Unlimited mode
      usageState = (
        <>
          <ProgressDiv>Unlimited Access</ProgressDiv>
        </>
      );
    } else if (!usageQuota.jobs_reached) {
      // max usage has not been reached
      usageState = (
        <ProgressDiv>
          <p>Usage</p>
          <CircularProgressWithLabel value={usagePercentage} colorOfTextLabel={colorOfTextLabel} />
          <ProgressP>{`${actualUploads}/${maxUploads} Analysis used`}</ProgressP>
        </ProgressDiv>
      );
    } else {
      // not unlimited account and
      // usage max is reached and
      // plan has expired
      usageState = <ExpiredP>Plan Has Expired</ExpiredP>;
    }
    return usageState;
  };

  return <>{CorrectCardComponent()}</>;
}
