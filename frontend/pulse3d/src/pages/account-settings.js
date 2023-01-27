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
const numberToMonthName = {
  1: "January",
  2: "February",
  3: "March",
  4: "April",
  5: "May",
  6: "June",
  7: "July",
  8: "August",
  9: "September",
  10: "October",
  11: "November",
  12: "December",
};

export default function AccountSettings() {
  const { usageQuota } = useContext(AuthContext);
  const [jobsLimit, setJobsLimit] = useState(-1);
  const [currentJobUsage, setCurrentJobUsage] = useState(0);
  const [endMonth, setEndMonth] = useState(null);
  const [endDay, setEndDay] = useState(null);
  const [endYear, setEndYear] = useState(null);
  const [daysLeft, setDaysLeft] = useState(0);

  useEffect(() => {
    console.log(usageQuota);
    if (usageQuota) {
      setJobsLimit(usageQuota.limits.jobs);
      setCurrentJobUsage(usageQuota.current.jobs);
      const endDate = new Date(usageQuota.limits.end);
      const currentDate = new Date(Date.now());
      const daysOfPlanLeft = parseInt((endDate - currentDate) / (1000 * 60 * 60 * 24));
      setEndMonth(numberToMonthName[endDate.getMonth()]);
      console.log(endDate.getDay());
      setEndDay(endDate.getDay());
      setEndYear(endDate.getFullYear());
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
        subscriptionEndDate={`${endMonth} ${endDay} ${endYear}`}
        labeltextcolor="black"
        daysOfPlanLeft={daysLeft}
      />
      <UsageWidgetFull
        metricName="Analysis"
        limitUsage={jobsLimit}
        actualUsage={currentJobUsage}
        subscriptionName={"Basic"}
        subscriptionEndDate={`${endMonth} ${endDay} ${endYear}`}
        labeltextcolor="black"
        daysOfPlanLeft={daysLeft}
      />
    </BackgroundContainer>
  );
}

AccountSettings.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
