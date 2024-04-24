import DashboardLayout from "@/components/layouts/DashboardLayout";
import { useContext, useEffect, useState } from "react";
import { AuthContext } from "@/pages/_app";
import styled from "styled-components";
import UsageWidgetFull from "@/components/account/UsageWidgetFull";
import AdminAccountOptions from "@/components/account/AdminAccountOptions";
import AnalysisParamContainer from "@/components/uploadForm/AnalysisParamContainer";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import { UploadsContext } from "@/pages/_app";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import PasswordForm from "@/components/account/PasswordForm";
import semverGte from "semver/functions/gte";
import { getMinP3dVersionForProduct } from "@/utils/generic";

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

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  padding-top: 2%;
`;

const SubsectionContainer = styled.div`
  margin-left: 50px;
  margin-right: 50px;
`;

const PasswordContainer = styled.div`
  margin-bottom: 17px;
  padding: 0 15%;
  position: relative;
  width: 100%;
  justify-content: center;
  display: flex;
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

const isEmpty = (str) => str === undefined || str.length === 0;

const filterP3dVersionsForProduct = (productType, versions) => {
  const minVersion = getMinP3dVersionForProduct(productType);
  return versions.filter((v) => semverGte(v, minVersion));
};

export default function AccountSettings() {
  const { accountType, usageQuota, accountId, productPage, preferences } = useContext(AuthContext);
  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);
  const [jobsLimit, setJobsLimit] = useState(-1);
  const [currentJobUsage, setCurrentJobUsage] = useState(0);
  const [endDate, setEndDate] = useState(null);
  const [daysLeft, setDaysLeft] = useState(0);
  const [pulse3dVersionOptions, setPulse3dVersionOptions] = useState([]);
  const [userPreferences, setUserPreferences] = useState({ version: 0 });
  const [inProgress, setInProgress] = useState({ password: false, preferences: false });
  const [errorMsg, setErrorMsg] = useState();
  const [passwords, setPasswords] = useState({ password1: "", password2: "" });
  const [filteredP3dVersions, setFilteredP3dVersions] = useState(pulse3dVersions);

  useEffect(() => {
    setFilteredP3dVersions(
      pulse3dVersions && productPage ? filterP3dVersionsForProduct(productPage, pulse3dVersions) : []
    );
  }, [pulse3dVersions, productPage]);

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
    const preferredVersion = preferences?.[productPage]?.version;
    if (preferredVersion != null && filteredP3dVersions.length > 0) {
      setUserPreferences({ version: filteredP3dVersions.indexOf(preferredVersion) });
    }
  }, [preferences, filteredP3dVersions, productPage]);

  useEffect(() => {
    if (filteredP3dVersions.length > 0) {
      const options = filteredP3dVersions.map((version) => {
        const selectedVersionMeta = metaPulse3dVersions.find((meta) => meta.version === version);
        return selectedVersionMeta && ["testing", "deprecated"].includes(selectedVersionMeta.state)
          ? version + `  [ ${selectedVersionMeta.state} ]`
          : version;
      });

      setPulse3dVersionOptions(options);
    }
  }, [filteredP3dVersions, metaPulse3dVersions]);

  const handlePulse3dVersionSelect = (idx) => {
    setUserPreferences({ ...userPreferences, version: idx });
  };

  const savePreferences = async () => {
    try {
      setInProgress({ ...inProgress, preferences: true });

      await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/preferences`, {
        method: "PUT",
        body: JSON.stringify({
          product: productPage,
          changes: { ...userPreferences, version: filteredP3dVersions[userPreferences.version] },
        }),
      });

      setInProgress({ ...inProgress, preferences: false });
    } catch (e) {
      console.log("ERROR updating user preferences");
    }
  };

  const onChangePassword = ({ target }) => {
    setPasswords({ ...passwords, [target.id]: target.value });
  };

  const saveNewPassword = async () => {
    try {
      setInProgress({ ...inProgress, password: true });

      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/${accountId}`, {
        method: "PUT",
        body: JSON.stringify({ passwords, action_type: "set_password" }),
      });

      const resBody = await res.json();

      if (res.status === 200) {
        if (!resBody) {
          setPasswords({ password1: "", password2: "" });
        } else if (resBody.message.includes("Cannot set password to any of the previous")) {
          setErrorMsg(`*${resBody.message}`);
        }
      } else {
        setErrorMsg("*Internal error. Please try again later.");
      }

      setInProgress({ ...inProgress, password: false });
    } catch (e) {
      console.log(e);
      setPasswords({ password1: "", password2: "" });
    }
  };

  return (
    <BackgroundContainer>
      <Header>Account Settings</Header>
      <SubsectionContainer>
        <Subheader>Change Password</Subheader>
        <SubSectionBody>
          <PasswordContainer>
            <PasswordForm
              password1={passwords.password1}
              password2={passwords.password2}
              onChangePassword={onChangePassword}
              setErrorMsg={setErrorMsg}
            >
              <ErrorText role="errorMsg">{errorMsg}</ErrorText>
            </PasswordForm>
          </PasswordContainer>

          <ButtonContainer>
            <ButtonWidget
              width="150px"
              height="40px"
              position="relative"
              borderRadius="3px"
              label="Save"
              backgroundColor={
                inProgress.password ||
                !(isEmpty(errorMsg) && !isEmpty(passwords.password1) && !isEmpty(passwords.password2))
                  ? "var(--dark-gray)"
                  : "var(--dark-blue)"
              }
              inProgress={inProgress.password}
              disabled={inProgress.password}
              clickFn={saveNewPassword}
            />
          </ButtonContainer>
        </SubSectionBody>
      </SubsectionContainer>
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
                width="150px"
                height="40px"
                position="relative"
                borderRadius="3px"
                label="Save"
                backgroundColor={inProgress.preferences ? "var(--dark-gray)" : "var(--dark-blue)"}
                inProgress={inProgress.preferences}
                disabled={inProgress.preferences}
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
