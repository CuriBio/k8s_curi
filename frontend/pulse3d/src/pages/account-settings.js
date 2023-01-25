import DashboardLayout from "@/components/layouts/DashboardLayout";
import { useContext, useEffect, useState } from "react";
import { AuthContext } from "@/pages/_app";
import styled from "styled-components";
import UsageWidgetFull from "@/components/basicWidgets/UsageWidgetFull";
import { useRouter } from "next/router";

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
  const router = useRouter();
  const { usageQuota } = useContext(AuthContext);
  const [jobsLimit, setJobsLimit] = useState(-1);
  const [currentJobUsage, setCurrentJobUsage] = useState(0);
  const [tabSelection, setTabSelection] = useState(router.query.id);
  useEffect(() => {
    console.log(usageQuota);
    if (usageQuota) {
      setJobsLimit(usageQuota.limits.jobs);
      setCurrentJobUsage(usageQuota.current.jobs);
    }
  }, [usageQuota]);
  useEffect(() => {
    // reset all params if the user switches between the "re-analyze" and "new upload" versions of this page
    setTabSelection(router.query.id);
  }, [router.query]);
  return (
    <BackgroundContainer>
      {tabSelection === "Plan Details" ? (
        <>
          <UsageWidgetFull
            metricName="Analysis"
            limitUsage={jobsLimit}
            actualUsage={currentJobUsage}
            subscriptionName={"Basic"}
            subscriptionEndDate={"mm/dd/yyyy"}
            labelColor="black"
          />
          <UsageWidgetFull
            metricName="Analysis"
            limitUsage={jobsLimit}
            actualUsage={currentJobUsage}
            subscriptionName={"Basic"}
            subscriptionEndDate={"mm/dd/yyyy"}
            labelColor="black"
          />
          <UsageWidgetFull
            metricName="Analysis"
            limitUsage={jobsLimit}
            actualUsage={currentJobUsage}
            subscriptionName={"Basic"}
            subscriptionEndDate={"mm/dd/yyyy"}
            labelColor="black"
          />
          <UsageWidgetFull
            metricName="Analysis"
            limitUsage={jobsLimit}
            actualUsage={currentJobUsage}
            subscriptionName={"Basic"}
            subscriptionEndDate={"mm/dd/yyyy"}
            labelColor="black"
          />
        </>
      ) : (
        <div>d</div>
      )}
    </BackgroundContainer>
  );
}

AccountSettings.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
