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

const getUsageEndpoint = (productPage) => {
  if (["mantarray", "nautilai"].includes(productPage)) {
    return `${process.env.NEXT_PUBLIC_PULSE3D_URL}/usage?service=${productPage}`;
  } else if (productPage === "advanced_analysis") {
    return `${process.env.NEXT_PUBLIC_ADVANCED_ANALYSIS_URL}/usage`;
  }
};

export default function UsageProgressWidget({ colorOfTextLabel }) {
  const { usageQuota, setUsageQuota, productPage } = useContext(AuthContext);

  const [newPlanModalIsOpen, setNewPlanModalIsOpen] = useState(false);

  const getUsageQuota = async () => {
    if (!productPage) {
      return;
    }

    try {
      const url = getUsageEndpoint(productPage);
      const response = await fetch(url);
      if (response && response.status === 200) {
        setUsageQuota(await response.json());
      }
    } catch (e) {
      console.log("ERROR fetching usage quota in /usage");
    }
  };

  useEffect(() => {
    if (productPage && Object.keys(usageQuota || {}).length === 0) {
      getUsageQuota();
    }
  }, [productPage]);

  const maxJobs = parseInt(usageQuota?.limits.jobs || 0);
  const currentNumJobs = parseInt(usageQuota?.current.jobs || 0);
  const usagePercentage = Math.min(Math.round((currentNumJobs / maxJobs) * 100), 100) || 0;
  const isExpired = usageQuota?.jobs_reached || false;

  const UpgradeButtonElement = (
    <UpgradeButton
      onClick={() => {
        setNewPlanModalIsOpen(true);
      }}
    >
      UPGRADE
    </UpgradeButton>
  );

  const getDisplay = () => {
    if (isExpired) {
      return (
        <ExpiredDiv>
          <DropDownStyleContainer>
            Plan Has Expired
            {UpgradeButtonElement}
          </DropDownStyleContainer>
        </ExpiredDiv>
      );
    } else if (maxJobs === -1) {
      return <ProgressDiv>Unlimited Access</ProgressDiv>;
    } else {
      return (
        <ProgressDiv>
          <p>Usage</p>
          <CircularProgressWithLabel value={usagePercentage} colorOfTextLabel={colorOfTextLabel} />
          <ProgressLabel>{`${currentNumJobs}/${maxJobs} analyses used`}</ProgressLabel>
          {UpgradeButtonElement}
        </ProgressDiv>
      );
    }
  };

  return (
    <>
      {getDisplay()}
      <ModalWidgetStyle>
        <ModalWidget
          open={newPlanModalIsOpen}
          labels={["Please email Curibio at contact@curibio.com to sign up for a new plan."]}
          closeModal={() => {
            setNewPlanModalIsOpen(false);
          }}
          header={"Contact"}
        />
      </ModalWidgetStyle>
    </>
  );
}
