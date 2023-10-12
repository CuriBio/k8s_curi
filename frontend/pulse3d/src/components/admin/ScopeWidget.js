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

export default function ScopeWidget({
  initialChecked = [],
  selectedScopes,
  setSelectedScopes,
  availableScopes,
  isForUser,
}) {
  const [scopeOptions, setScopeOptions] = useState([]);
  const [scopeDisabledStates, setScopeDisabledStates] = useState([]);

  useEffect(() => {
    formatUserScopes();
  }, [availableScopes]);

  useEffect(() => {
    if (initialChecked.length > 0) {
      setSelectedScopes(initialChecked);
    }
  }, [initialChecked]);

  useEffect(() => {
    handleScopeDisabledStates();
  }, [selectedScopes]);

  const formatUserScopes = () => {
    // customer scopes are an array, user scopes are an object
    const scopeList = isForUser
      ? Object.entries(availableScopes).map(([product, addScopes]) => [product, addScopes])
      : availableScopes;

    const flattenedScopes = scopeList.flat(2);

    setScopeOptions(flattenedScopes);
    handleScopeDisabledStates();
  };

  const handleScopeDisabledStates = (selected = selectedScopes) => {
    const disabledStates = isForUser
      ? disableUserScopes(selected)
      : Array(availableScopes.length).fill(false);

    setScopeDisabledStates(disabledStates);
  };

  const disableUserScopes = (selected) => {
    const disabledStates = [];
    Object.entries(availableScopes).map(([product, addScopes]) => {
      // product itself is always enabled
      disabledStates.push(false);
      // if main product is checked, then enabled other scope options under product
      // example: nautilus:rw_all_data
      Array(addScopes.length)
        .fill()
        .map(() => disabledStates.push(!selected.includes(product)));
    });

    return disabledStates;
  };

  const handleCheckedScopes = (scope, state) => {
    const newCheckedScopes = JSON.parse(JSON.stringify(selectedScopes));

    if (state && !newCheckedScopes.includes(scope)) {
      newCheckedScopes.push(scope);
    } else {
      newCheckedScopes.splice(newCheckedScopes.indexOf(scope), 1);
      // if main product scope is being unchecked, auto uncheck any dependent scopes if checked
      // example: 'mantarray' is unchecked, ensure that 'mantarray:rw_all_data' is unchecked
      if (Object.keys(availableScopes).includes(scope)) {
        for (const s of availableScopes[scope]) {
          if (newCheckedScopes.includes(s)) {
            newCheckedScopes.splice(newCheckedScopes.indexOf(s), 1);
          }
        }
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
