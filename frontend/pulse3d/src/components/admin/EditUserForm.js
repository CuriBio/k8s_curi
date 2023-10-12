import styled from "styled-components";
import { useState, useEffect, useContext } from "react";
import ScopeWidget from "./ScopeWidget";
import { AuthContext } from "@/pages/_app";
import ModalWidget from "@/components/basicWidgets/ModalWidget";

const BodyContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  margin-bottom: 10px;
`;

export default function EditUserForm({ userData, openEditModal, setOpenEditModal, resetTable }) {
  const [selectedScopes, setSelectedScopes] = useState([]);
  const [existingScopes, setExistingScopes] = useState([]);
  const [buttons, setButtons] = useState(["Close", "Save"]);
  const [labels, setLabels] = useState([]);

  const { availableScopes } = useContext(AuthContext);

  useEffect(() => {
    if (userData && availableScopes.user) {
      const scopeList = Object.entries(availableScopes.user).map(([product, addScopes]) => [
        product,
        addScopes,
      ]);
      const flattenedScopes = scopeList.flat(2);

      let displayedScopes = userData.scopes.map((s) => {
        if (flattenedScopes.includes(s)) return s;
        else return s.split(":")[0];
      });

      displayedScopes = [...new Set(displayedScopes)];
      setExistingScopes(displayedScopes);
    }
  }, [userData, availableScopes]);

  const handleButtonSelection = async (idx) => {
    if (idx === 1) {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/scopes/${userData.id}`, {
          method: "PUT",
          body: JSON.stringify({ scopes: selectedScopes }),
        });

        if (res.status === 204) {
          setOpenEditModal(false);
          resetTable();
        } else {
          throw Error;
        }
      } catch (e) {
        setButtons(["Close"]);
        setLabels(["An error occurred while updating user.", "Please try again later."]);
      }
    } else {
      setOpenEditModal(false);
      resetTable();
    }
  };

  return (
    <ModalWidget
      open={openEditModal}
      width={600}
      closeModal={handleButtonSelection}
      header={"Edit User"}
      labels={labels}
      buttons={buttons}
    >
      {labels.length === 0 && (
        <BodyContainer>
          <ScopeWidget
            selectedScopes={selectedScopes}
            setSelectedScopes={setSelectedScopes}
            initialChecked={existingScopes}
          />
        </BodyContainer>
      )}
    </ModalWidget>
  );
}
