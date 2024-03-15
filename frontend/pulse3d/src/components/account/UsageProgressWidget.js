import { useEffect, useState } from "react";
import CircularProgressWithLabel from "@/components/basicWidgets/CircularProgressWithLabel";
import { useContext } from "react";
import { AuthContext } from "@/pages/_app";
import styled from "styled-components";
import ModalWidget from "@/components/basicWidgets/ModalWidget";

const ProgressDiv = styled.div`
  color: white;
  display: flex;
  align-items: center;
  column-count: 1;
  column-gap: 10px;
  cursor: default;
`;
const ProgressLabel = styled.div`
  font-size: 0.85rem;
`;
const ExpiredDiv = styled.div`
  color: white;
`;

const DropDownStyleContainer = styled.div`
  display: flex;
  flex-flow: row;
  align-items: center;
  height: 100%;
  justify-content: space-around;
`;

const ModalWidgetStyle = styled.div`
  position: absolute;
`;

const UpgradeButton = styled.div`
  color: var(--light-gray);
  font-size: 12px;
  margin-left: 15px;
  text-decoration: underline;
  &:hover {
    color: var(--teal-green);
    cursor: pointer;
  }
`;

export default function UsageProgressWidget({ colorOfTextLabel }) {
  const { usageQuota, setUsageQuota, productPage } = useContext(AuthContext);

  const [maxAnalyses, setMaxAnalyses] = useState(0);
  const [actualAnalyses, setActualAnalyses] = useState();
  const [usagePercentage, setUsagePercentage] = useState(0);
  const [isExpired, setIsExpired] = useState();
  const [newPlanModalIsOpen, setNewPlanModalIsOpen] = useState(false);

  const pollUsageQuota = async () => {
    if (!productPage) {
      return;
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_PULSE3D_URL}/usage?service=${productPage}`,
      );
      if (response && response.status === 200) {
        const newUsageQuota = await response.json();

        const limit = parseInt(newUsageQuota.limits.jobs);
        const actual = parseInt(newUsageQuota.current.jobs);
        const newUsagePercentage = Math.round((actual / limit) * 100);

        setUsagePercentage(newUsagePercentage > 100 ? 100 : newUsagePercentage);
        setActualAnalyses(newUsageQuota.current.jobs);
        setIsExpired(newUsageQuota.jobs_reached);
        setUsageQuota({
          current: {
            jobs: newUsageQuota.current.jobs,
            uploads: newUsageQuota.current.uploads,
          },
          jobs_reached: newUsageQuota.jobs_reached,
          limits: {
            jobs: newUsageQuota.limits.jobs,
            uploads: newUsageQuota.limits.uploads,
            expiration_date: newUsageQuota.limits.expiration_date,
          },
          uploads_reached: newUsageQuota.uploads_reached,
        });
        setMaxAnalyses(limit);
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
      setUsagePercentage(usagePercentage > 100 ? 100 : usagePercentage);
      setIsExpired(usageQuota.jobs_reached);
    }
    pollUsageQuota();
  }, []);

  useEffect(() => {
    if (maxAnalyses !== -1 && productPage) {
      const pollingUsageQuota = setInterval(async () => {
        await pollUsageQuota();
      }, 1e4);

      return () => clearInterval(pollingUsageQuota);
    }
  }, [productPage]);

  const UpgradeButtonElement = (
    <UpgradeButton
      onClick={() => {
        setNewPlanModalIsOpen(true);
      }}
    >
      UPGRADE
    </UpgradeButton>
  );

  return (
    <>
      {maxAnalyses === -1 && <ProgressDiv>Unlimited Access</ProgressDiv>}
      {!isExpired && maxAnalyses !== -1 && (
        <ProgressDiv>
          <p>Usage</p>
          <CircularProgressWithLabel
            value={usagePercentage}
            colorOfTextLabel={colorOfTextLabel}
          />
          <ProgressLabel>{`${actualAnalyses || 0}/${maxAnalyses} Analysis used`}</ProgressLabel>
          {UpgradeButtonElement}
        </ProgressDiv>
      )}
      {isExpired && (
        <ExpiredDiv>
          <DropDownStyleContainer>
            Plan Has Expired
            {UpgradeButtonElement}
          </DropDownStyleContainer>
        </ExpiredDiv>
      )}
      <ModalWidgetStyle>
        <ModalWidget
          open={newPlanModalIsOpen}
          labels={[
            "Please email Curibio at contact@curibio.com to sign up for a new plan.",
          ]}
          closeModal={() => {
            setNewPlanModalIsOpen(false);
          }}
          header={"Contact"}
        />
      </ModalWidgetStyle>
    </>
  );
}
