import DashboardLayout from "@/components/layouts/DashboardLayout";
import { useContext, useEffect, useState } from "react";
import { AuthContext } from "@/pages/_app";
import styled from "styled-components";
import UsageWidgetFull from "@/components/account/UsageWidgetFull";
import AdminAccountOptions from "@/components/account/AdminAccountOptions";
import AnalysisParamContainer from "@/components/uploadForm/AnalysisParamContainer";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import { UploadsContext } from "@/components/layouts/DashboardLayout";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";

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

const DropDownContainer = styled.div`
  width: 57%;
  height: 89%;
  background: white;
  border-radius: 5px;
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
  padding: 15px;
`;

const Subheader = styled.h2`
  position: relative;
  text-align: left;
  margin: 0px;
  margin-left: 30px;
  margin-top: 8px;
  width: 100%;
  height: 65px;
  line-height: 3;
`;

const ButtonContainer = styled.div`
  display: flex;
  justify-content: flex-end;
  padding-right: 45px;
`;

export default function AccountSettings() {
  const { accountType, usageQuota, accountId, productPage } = useContext(AuthContext);
  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);
  const [jobsLimit, setJobsLimit] = useState(-1);
  const [currentJobUsage, setCurrentJobUsage] = useState(0);
  const [endDate, setEndDate] = useState(null);
  const [daysLeft, setDaysLeft] = useState(0);
  const [pulse3dVersionOptions, setPulse3dVersionOptions] = useState([]);
  const [userPreferences, setUserPreferences] = useState({ version: 0 });
  const [inProgress, setInProgress] = useState(false);

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

  useEffect(() => {
    if (pulse3dVersions) {
      const options = pulse3dVersions.map((version) => {
        const selectedVersionMeta = metaPulse3dVersions.filter((meta) => meta.version === version);
        return selectedVersionMeta[0] && ["testing", "deprecated"].includes(selectedVersionMeta[0].state)
          ? version + `  [ ${selectedVersionMeta[0].state} ]`
          : version;
      });

      setPulse3dVersionOptions(options);
    }
  }, [pulse3dVersions, metaPulse3dVersions]);

  const handlePulse3dVersionSelect = (idx) => {
    setUserPreferences({ ...userPreferences, version: idx });
  };

  const savePreferences = async () => {
    try {
      setInProgress(true);

      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/preferences`, {
        method: "PUT",
        body: JSON.stringify({
          product: productPage,
          changes: { ...userPreferences, version: pulse3dVersions[userPreferences.version] },
        }),
      });

      setInProgress(false);
    } catch (e) {
      console.log("ERROR updating user preferences");
    }
  };

  return (
    <BackgroundContainer>
      <Header>Account Settings</Header>
      {!isAdminAccount && (
        <SubsectionContainer>
          <Subheader>Preferences</Subheader>
          <SubSectionBody>
            <AnalysisParamContainer
              label="Pulse3D Version"
              name="selectedPulse3dVersion"
              tooltipText="Specifies which version of the Pulse3D analysis software to use."
              additionalLabelStyle={{ lineHeight: 1.5 }}
              iconStyle={{ fontSize: 20, margin: "2px 10px" }}
            >
              <DropDownContainer>
                <DropDownWidget
                  options={pulse3dVersionOptions}
                  handleSelection={handlePulse3dVersionSelect}
                  initialSelected={userPreferences.version}
                />
              </DropDownContainer>
            </AnalysisParamContainer>
            <ButtonContainer>
              <ButtonWidget
                width="200px"
                height="50px"
                position="relative"
                borderRadius="3px"
                label="Save"
                inProgress={inProgress}
                clickFn={savePreferences}
              />
            </ButtonContainer>
          </SubSectionBody>
        </SubsectionContainer>
      )}
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
