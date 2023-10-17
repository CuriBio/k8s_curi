import styled from "styled-components";
import { useState, useEffect, useContext } from "react";
import CheckboxList from "@/components/basicWidgets/CheckboxList";
import { AuthContext } from "@/pages/_app";

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

export default function ScopeWidget({ initialChecked = [], selectedScopes, setSelectedScopes }) {
  const [scopeOptions, setScopeOptions] = useState([]);
  const [scopeDisabledStates, setScopeDisabledStates] = useState([]);

  const { userScopes } = useContext(AuthContext);

  useEffect(() => {
    if (userScopes) {
      formatUserScopes();
    }
  }, [userScopes]);

  useEffect(() => {
    if (initialChecked.length > 0) {
      setSelectedScopes(initialChecked);
    }
  }, [initialChecked]);

  useEffect(() => {
    handleScopeDisabledStates();
  }, [selectedScopes]);

  const formatUserScopes = () => {
    const scopeList = Object.entries(userScopes).map(([product, addScopes]) => [product, addScopes]);
    const flattenedScopes = scopeList.flat(2);
    setScopeOptions(flattenedScopes);
    handleScopeDisabledStates();
  };

  const handleScopeDisabledStates = (selected = selectedScopes) => {
    const disabledStates = [];
    Object.entries(userScopes).map(([product, addScopes]) => {
      // product itself is always enabled
      disabledStates.push(false);
      // if main product is checked, then enabled other scope options under product
      // example: nautilus:rw_all_data
      Array(addScopes.length)
        .fill()
        .map(() => disabledStates.push(!selected.includes(product)));
    });

    setScopeDisabledStates(disabledStates);
  };

  const handleCheckedScopes = (scope, state) => {
    const newCheckedScopes = JSON.parse(JSON.stringify(selectedScopes));

    if (state && !newCheckedScopes.includes(scope)) {
      newCheckedScopes.push(scope);
    } else {
      newCheckedScopes.splice(newCheckedScopes.indexOf(scope), 1);
      // if main product scope is being unchecked, auto uncheck any dependent scopes if checked
      // example: 'mantarray' is unchecked, ensure that 'mantarray:rw_all_data' is unchecked
      if (Object.keys(userScopes).includes(scope)) {
        for (const s of userScopes[scope]) {
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
