import DashboardLayout from "@/components/layouts/DashboardLayout";
import { useContext, useEffect, useState } from "react";
import { AuthContext } from "@/pages/_app";
import styled from "styled-components";
import UsageWidgetFull from "@/components/basicWidgets/UsageWidgetFull";
import AdminAccountOptions from "@/components/account/AdminAccountOptions";

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  width: 90%;
  min-width: 1200px;
  border: solid;
  border-color: var(--dark-gray);
  border-width: 2px;
  border-radius: 15px;
  background-color: white;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin: 5%;
  align-items: left;
  padding-bottom: 3%;
`;

const Header = styled.h2`
  position: relative;
  text-align: center;
  background-color: var(--dark-blue);
  color: var(--light-gray);
  margin: 0px;
  width: 100%;
  height: 75px;
  line-height: 3;
`;

const SubsectionContainer = styled.div`
  margin-left: 50px;
  margin-right: 50px;
`;

const SubSectionBody = styled.div`
  background-color: var(--light-gray);
  border: solid;
  border-width: 2px;
  border-color: var(--dark-gray);
  border-radius: 15px;
  display: flex;
  flex-direction: column;
  padding-block: 30px;
  padding-inline: 40px;
`;

const Subheader = styled.h2`
  position: relative;
  text-align: left;
  margin: 0px;
  margin-left: 30px;
  margin-top: 30px;
  width: 100%;
  height: 75px;
  line-height: 3;
`;

export default function AccountSettings() {
  const { accountType, usageQuota, accountId } = useContext(AuthContext);
  const [jobsLimit, setJobsLimit] = useState(-1);
  const [currentJobUsage, setCurrentJobUsage] = useState(0);
  const [endDate, setEndDate] = useState(null);
  const [daysLeft, setDaysLeft] = useState(0);

  const isAdminAccount = accountType === "admin";

  useEffect(() => {
    if (usageQuota && usageQuota.limits && usageQuota.current) {
      setJobsLimit(usageQuota.limits.jobs);
      setCurrentJobUsage(usageQuota.current.jobs);

      // account for edge case that expiration date is null
      if (usageQuota.limits.expiration_date) {
        const endDate = new Date(usageQuota.limits.expiration_date).toUTCString();
        setEndDate(endDate.slice(0, 16));

        const currentDate = new Date(new Date(Date.now()).toUTCString());
        const daysOfPlanLeft = parseInt((new Date(endDate) - currentDate) / (1000 * 60 * 60 * 24));
        setDaysLeft(daysOfPlanLeft);
      }
    }
  }, [usageQuota]);

  return (
    <BackgroundContainer>
      <Header>Account Settings</Header>
      <SubsectionContainer>
        <Subheader>Usage Details</Subheader>
        <SubSectionBody>
          <UsageWidgetFull
            metricName="Analysis"
            limitUsage={jobsLimit}
            actualUsage={currentJobUsage}
            daysLeft={daysLeft}
            subscriptionEndDate={endDate}
            colorOfTextLabel="black"
            daysOfPlanLeft={daysLeft}
          />
        </SubSectionBody>
      </SubsectionContainer>
      {isAdminAccount && (
        <SubsectionContainer>
          <Subheader>Edit Organization Settings</Subheader>
          <SubSectionBody>
            <AdminAccountOptions accountId={accountId} />
          </SubSectionBody>
        </SubsectionContainer>
      )}
    </BackgroundContainer>
  );
}

AccountSettings.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
