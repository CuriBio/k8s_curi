import styled from "styled-components";
import { useState, useEffect, useContext } from "react";
import ScopeWidget from "./ScopeWidget";
import { AuthContext } from "@/pages/_app";

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  margin-bottom: 10px;
`;

export default function EditUserForm({ userData }) {
  const [selectedScopes, setSelectedScopes] = useState([]);
  const [existingScopes, setExistingScopes] = useState([]);
  const { userScopes } = useContext(AuthContext);

  useEffect(() => {
    const scopeList = Object.entries(userScopes).map(([product, addScopes]) => [product, addScopes]);
    const flattenedScopes = scopeList.flat(2);

    let displayedScopes = userData.scopes.map((s) => {
      if (flattenedScopes.includes(s)) return s;
      else return s.split(":")[0];
    });

    displayedScopes = [...new Set(displayedScopes)];
    setExistingScopes(displayedScopes);
  }, [userData]);

  return (
    <BackgroundContainer>
      <ScopeWidget
        selectedScopes={selectedScopes}
        setSelectedScopes={setSelectedScopes}
        initialChecked={existingScopes}
      />
    </BackgroundContainer>
  );
}
