import { UploadsContext } from "@/pages/_app";
import { useContext, useEffect, useState } from "react";
import styled from "styled-components";
import AnalysisParamContainer from "@/components/uploadForm/AnalysisParamContainer";
import DropDownWidget from "@/components/basicWidgets/DropDownWidget";

const DropDownContainer = styled.div`
  width: 57%;
  height: 89%;
  background: white;
  border-radius: 5px;
`;

export default function VersionWidget({ selectedP3dVersion, setSelectedP3dVersion }) {
  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);
  const [pulse3dVersionOptions, setPulse3dVersionOptions] = useState([]);

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
    setSelectedP3dVersion(idx);
  };

  return (
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
          initialSelected={selectedP3dVersion}
        />
      </DropDownContainer>
    </AnalysisParamContainer>
  );
}
