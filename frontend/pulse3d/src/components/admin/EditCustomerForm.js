import styled from "styled-components";
import { useState, useEffect } from "react";
import ScopeWidget from "./ScopeWidget";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import CheckboxList from "@/components/basicWidgets/CheckboxList";

const BodyContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: start;
  flex-direction: column;
  margin: 5% 10%;
`;

const StaticInfo = styled.div`
  position: relative;
  display: flex;
  justify-content: start;
  align-items: center;
  flex-direction: row;
  margin: 15px 10%;
  width: 100%;
`;

const StaticLabel = styled.div`
  width: 80px;
`;

const ProductBox = styled.div``;

export default function EditCustomerForm({ customerData, openEditModal, setOpenEditModal, resetTable }) {
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [buttons, setButtons] = useState(["Cancel", "Save"]);
  const [labels, setLabels] = useState([]);

  // useEffect(() => {
  //   if (userData) {
  //     const existingScopes = userData.scopes.filter((scope) =>
  //       Object.keys(availableScopes.user).includes(scope)
  //     );
  //     setSelectedScopes(existingScopes);
  //   }
  // }, [userData]);
  console.log(customerData);

  const handleButtonSelection = async (idx) => {
    if (idx === 1) {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/scopes/${customerData.id}`, {
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
      open={typeof openEditModal == "object" || openEditModal}
      width={700}
      closeModal={handleButtonSelection}
      header={"Edit Customer"}
      labels={labels}
      buttons={buttons}
    >
      <StaticInfo>
        <StaticLabel>ID:</StaticLabel>
        {customerData.id}
      </StaticInfo>
      <StaticInfo>
        <StaticLabel>Email:</StaticLabel>
        {customerData.email}
      </StaticInfo>
      <BodyContainer>
        <StaticLabel>Products:</StaticLabel>
        <CheckboxList
          height="150px"
          width="100%"
          options={["mantarray", "nautilai"]}
          checkedItems={selectedProducts}
          setCheckedItems={}
        />
        <StaticLabel style={{ width: "150px" }}>Usage Restrictions:</StaticLabel>
      </BodyContainer>
    </ModalWidget>
  );
}
