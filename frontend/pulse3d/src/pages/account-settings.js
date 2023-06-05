import DashboardLayout from "@/components/layouts/DashboardLayout";
import { useContext, useEffect, useState } from "react";
import { AuthContext } from "@/pages/_app";
import styled from "styled-components";
import UsageWidgetFull from "@/components/basicWidgets/UsageWidgetFull";

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: 1fr 1fr 1fr;
  grid-gap: 2rem;
  justify-content: space-around;
  height: 100%;
  width: 85%;
  padding: 1rem;
`;

export default function AccountSettings() {
  const { usageQuota } = useContext(AuthContext);
  const [jobsLimit, setJobsLimit] = useState(-1);
  const [currentJobUsage, setCurrentJobUsage] = useState(0);
  const [endDate, setEndDate] = useState(null);
  const [daysLeft, setDaysLeft] = useState(0);

  useEffect(() => {
    if (usageQuota && usageQuota.limits && usageQuota.current) {
      setJobsLimit(usageQuota.limits.jobs);
      setCurrentJobUsage(usageQuota.current.jobs);

      const endDate = new Date(usageQuota.limits.expiration_date).toUTCString();
      setEndDate(endDate.slice(0, 16));

      const currentDate = new Date(new Date(Date.now()).toUTCString());
      const daysOfPlanLeft = parseInt((new Date(endDate) - currentDate) / (1000 * 60 * 60 * 24));
      setDaysLeft(daysOfPlanLeft);
    }
  }, [usageQuota]);
  return (
    <BackgroundContainer>
      <UsageWidgetFull
        metricName="Analysis"
        limitUsage={jobsLimit}
        actualUsage={currentJobUsage}
        subscriptionName={"Basic"}
        daysLeft={daysLeft}
        subscriptionEndDate={endDate}
        colorOfTextLabel="black"
        daysOfPlanLeft={daysLeft}
      />
    </BackgroundContainer>
  );
}

AccountSettings.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
