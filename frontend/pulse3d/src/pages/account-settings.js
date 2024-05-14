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
import UserPreferences from "@/components/account/UserPreferences";

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

const SuccessText = styled.span`
  color: green;
  text-align: left;
  position: relative;
  padding-top: 1%;
  padding-right: 2%;
`;

const ErrorText = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  padding-top: 1%;
  padding-right: 2%;
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

export default function AccountSettings() {
  const { accountType, usageQuota, accountId, productPage, preferences } = useContext(AuthContext);
  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);
  const [jobsLimit, setJobsLimit] = useState(-1);
  const [currentJobUsage, setCurrentJobUsage] = useState(0);
  const [endDate, setEndDate] = useState(null);
  const [passwordUpdateSuccess, setPasswordUpdateSuccess] = useState(false);
  const [daysLeft, setDaysLeft] = useState(0);
  const [inProgress, setInProgress] = useState({ password: false });
  const [errorMsg, setErrorMsg] = useState();
  const [passwords, setPasswords] = useState({ password1: "", password2: "" });

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

  const onChangePassword = ({ target }) => {
    setPasswordUpdateSuccess(false);
    setPasswords({ ...passwords, [target.id]: target.value });
  };

  const saveNewPassword = async () => {
    let newErrorMsg = null;
    try {
      setInProgress({ ...inProgress, password: true });

      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/${accountId}`, {
        method: "PUT",
        body: JSON.stringify({ passwords, action_type: "set_password" }),
      });

      // TODO this route probably shouldn't return a 200 if there is an error
      if (res.status === 200) {
        const resBody = await res.json();
        if (resBody?.message) {
          newErrorMsg = `*${resBody.message}`;
        }
      } else {
        newErrorMsg = "*Internal error. Please try again later.";
      }
    } catch (e) {
      console.log("ERROR updating password", e);
      newErrorMsg = "Error";
    }

    setInProgress({ ...inProgress, password: false });

    if (newErrorMsg) {
      setErrorMsg(newErrorMsg);
    } else {
      setPasswords({ password1: "", password2: "" });
      setPasswordUpdateSuccess(true);
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
            ></PasswordForm>
          </PasswordContainer>
          <ButtonContainer>
            {passwordUpdateSuccess && <SuccessText>Update Successful!</SuccessText>}
            {errorMsg && <ErrorText role="errorMsg">{errorMsg}</ErrorText>}
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
          <UserPreferences
            pulse3dVersions={pulse3dVersions}
            metaPulse3dVersions={metaPulse3dVersions}
            productPage={productPage}
            preferences={preferences}
          />
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
