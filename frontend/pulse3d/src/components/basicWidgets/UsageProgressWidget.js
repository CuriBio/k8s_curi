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
  cursor: default;
`;
const ProgressP = styled.p`
  font-size: 0.85rem;
`;
const ExpiredP = styled.p`
  color: white;
`;

export default function UsageProgressWidget({ colorOfTextLabel }) {
  const { usageQuota, setUsageQuota } = useContext(AuthContext);
  const [maxAnalyses, setMaxAnalyses] = useState();
  const [actualAnalyses, setActualAnalyses] = useState(0);
  const [usagePercentage, setUsagePercentage] = useState(0);
  const [isExpired, setIsExpired] = useState();
  const pollUsageQuota = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/usage`);
      if (response && response.status === 200) {
        const newUsageQuota = await response.json();
        const limit = parseInt(newUsageQuota.limits.jobs);
        const actual = parseInt(newUsageQuota.current.jobs);
        const newUsagePercentage = Math.round((actual / limit) * 100);
        if (newUsagePercentage > 100) {
          setUsagePercentage(100);
        } else {
          setUsagePercentage(newUsagePercentage);
        }
        setActualAnalyses(newUsageQuota["current"]["jobs"]);
        setIsExpired(newUsageQuota.jobs_reached);
        setUsageQuota(newUsageQuota);
      }
    } catch (e) {
      console.log("ERROR fetching usage quota in /usage");
    }
  };
  useEffect(() => {
    if (usageQuota && usageQuota.limits && usageQuota.current) {
      const limit = parseInt(usageQuota.limits.jobs);
      const actual = parseInt(usageQuota.current.jobs);
      setMaxAnalyses(limit);
      setActualAnalyses(actual);
      const usagePercentage = Math.round((actual / limit) * 100);
      if (usagePercentage > 100) {
        setUsagePercentage(100);
      } else {
        setUsagePercentage(usagePercentage);
      }
      setIsExpired(usageQuota.jobs_reached);
    }
  }, [usageQuota]);

  useEffect(() => {
    if (actualAnalyses) {
      const pollingUsageQuota = setInterval(async () => {
        await pollUsageQuota();
      }, [1e4]);

      return () => clearInterval(pollingUsageQuota);
    }
  }, [actualAnalyses]);

  return (
    <>
      {maxAnalyses === -1 && <ProgressDiv>Unlimited Access</ProgressDiv>}
      {!isExpired && maxAnalyses !== -1 && (
        <ProgressDiv>
          <p>Usage</p>
          <CircularProgressWithLabel value={usagePercentage} colorOfTextLabel={colorOfTextLabel} />
          <ProgressP>{`${actualAnalyses}/${maxAnalyses} Analysis used`}</ProgressP>
        </ProgressDiv>
      )}
      {isExpired && <ExpiredP>Plan Has Expired</ExpiredP>}
    </>
  );
}
