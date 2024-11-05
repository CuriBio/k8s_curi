import { useContext, useEffect, useState } from "react";
import styled from "styled-components";
import AnalysisParamContainer from "@/components/uploadForm/AnalysisParamContainer";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import semverGte from "semver/functions/gte";
import { getMinP3dVersionForAnalysis } from "@/utils/generic";

const DropDownContainer = styled.div`
  width: 57%;
  height: 89%;
  background: white;
  border-radius: 5px;
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

const filterP3dVersionsForProduct = (productType, versions) => {
  const minVersion = getMinP3dVersionForAnalysis(productType);
  return versions.filter((v) => semverGte(v, minVersion));
};

export default function UserPreferences({ pulse3dVersions, metaPulse3dVersions, productPage, preferences }) {
  const [pulse3dVersionOptions, setPulse3dVersionOptions] = useState([]);
  const [userPreferences, setUserPreferences] = useState({});
  const [filteredP3dVersions, setFilteredP3dVersions] = useState([]);
  const [inProgress, setInProgress] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState();

  useEffect(() => {
    setFilteredP3dVersions(
      pulse3dVersions && productPage ? filterP3dVersionsForProduct(productPage, pulse3dVersions) : []
    );
  }, [pulse3dVersions, productPage]);

  useEffect(() => {
    const preferredVersion = preferences?.[productPage]?.version;
    setUserPreferences({ version: preferredVersion == null ? "Latest" : preferredVersion });
  }, [preferences, productPage]);

  useEffect(() => {
    if (filteredP3dVersions.length > 0) {
      const options = filteredP3dVersions.map((version) => {
        const selectedVersionMeta = metaPulse3dVersions.find((meta) => meta.version === version);
        return selectedVersionMeta && ["testing", "deprecated"].includes(selectedVersionMeta.state)
          ? version + `  [ ${selectedVersionMeta.state} ]`
          : version;
      });

      setPulse3dVersionOptions(["Latest", ...options]);
    }
  }, [filteredP3dVersions, metaPulse3dVersions]);

  const handlePulse3dVersionSelect = (idx) => {
    setUpdateSuccess(false);
    setUserPreferences({ ...userPreferences, version: pulse3dVersionOptions[idx] });
  };

  const savePreferences = async () => {
    let newErrorMsg = null;
    try {
      setInProgress(true);

      const newP3dVersion = userPreferences.version === "Latest" ? null : userPreferences.version;

      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/preferences`, {
        method: "PUT",
        body: JSON.stringify({
          product: productPage,
          changes: { ...userPreferences, version: newP3dVersion },
        }),
      });

      if (res.status !== 200) {
        newErrorMsg = "Error";
      }
    } catch (e) {
      console.log("ERROR updating user preferences", e);
      newErrorMsg = "Error";
    }

    setInProgress(false);
    setErrorMsg(newErrorMsg);
    setUpdateSuccess(newErrorMsg === null);
  };
  return (
    <>
      <Subheader>Preferences</Subheader>
      <SubSectionBody>
        <AnalysisParamContainer
          label="Pulse3D Version"
          name="selectedPulse3dVersion"
          tooltipText="Specifies which version of the Pulse3D analysis software to use by default."
          additionalLabelStyle={{ lineHeight: 1.5 }}
          iconStyle={{ fontSize: 20, margin: "2px 10px" }}
        >
          <DropDownContainer>
            <DropDownWidget
              options={pulse3dVersionOptions}
              handleSelection={handlePulse3dVersionSelect}
              initialSelected={pulse3dVersionOptions.indexOf(userPreferences.version)}
            />
          </DropDownContainer>
        </AnalysisParamContainer>
        <ButtonContainer>
          {updateSuccess && <SuccessText>Update Successful!</SuccessText>}
          {errorMsg && <ErrorText role="errorMsg">{errorMsg}</ErrorText>}
          <ButtonWidget
            width="150px"
            height="40px"
            position="relative"
            borderRadius="3px"
            label="Save"
            backgroundColor={inProgress ? "var(--dark-gray)" : "var(--dark-blue)"}
            inProgress={inProgress}
            disabled={inProgress}
            clickFn={savePreferences}
          />
        </ButtonContainer>
      </SubSectionBody>
    </>
  );
}
