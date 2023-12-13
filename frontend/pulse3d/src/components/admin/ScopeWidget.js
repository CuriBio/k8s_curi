import styled from "styled-components";
import { useState, useEffect } from "react";
import CheckboxList from "@/components/basicWidgets/CheckboxList";

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  margin-bottom: 10px;
  width: 100%;
`;

const ScopeLabel = styled.div`
  position: relative;
  width: 80%;
  height: 30px;
  min-height: 30px;
  padding: 5px;
  line-height: 2;
`;

export default function ScopeWidget({ selectedScopes, setSelectedScopes, availableScopes }) {
  const [scopeOptions, setScopeOptions] = useState([]);
  const [scopeDisabledStates, setScopeDisabledStates] = useState([]);

  useEffect(() => {
    const newScopeOptions = [];
    const newScopeDisabledStates = [];

    Object.entries(availableScopes).map(([scope, requiredScope]) => {
      newScopeOptions.push(scope);
      newScopeDisabledStates.push(
        // Tanner (12/13/23): don't want to let users mess with this scope at the moment. Any user with mantarray:base should also have this scope
        scope === "mantarray:firmware:get" || (requiredScope && !selectedScopes.includes(requiredScope))
      );
    });

    setScopeOptions(newScopeOptions);
    setScopeDisabledStates(newScopeDisabledStates);
  }, [availableScopes, selectedScopes]);

  const handleCheckedScopes = (scope, checked) => {
    let newCheckedScopes = JSON.parse(JSON.stringify(selectedScopes));

    if (checked) {
      if (!newCheckedScopes.includes(scope)) {
        newCheckedScopes.push(scope);
        if (scope === "mantarray:base") {
          newCheckedScopes.push("mantarray:firmware:get");
        }
      }
    } else if (newCheckedScopes.includes(scope)) {
      newCheckedScopes.splice(newCheckedScopes.indexOf(scope), 1);
      let updated = [];
      let count = 0; // Tanner (12/13/23): this shouldn't be necessary but leaving here in case something breaks so that the page doesn't freeze
      while (count < 10) {
        count += 1;
        updated = newCheckedScopes.filter((scope) => {
          const requiredScope = availableScopes[scope];
          return !requiredScope || newCheckedScopes.includes(requiredScope);
        });
        if (updated.length === newCheckedScopes.length) break;
        newCheckedScopes = updated;
      }
    }
    setSelectedScopes(newCheckedScopes);
  };

  return (
    <BackgroundContainer>
      <ScopeLabel>Product Scopes:</ScopeLabel>
      <CheckboxList
        height="150px"
        width="80%"
        options={scopeOptions}
        disabled={scopeDisabledStates}
        checkedItems={selectedScopes}
        setCheckedItems={handleCheckedScopes}
      />
    </BackgroundContainer>
  );
}
