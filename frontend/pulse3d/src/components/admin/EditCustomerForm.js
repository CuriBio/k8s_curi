import styled from "styled-components";
import { useState, useEffect } from "react";
import FormInput from "@/components/basicWidgets/FormInput";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import CheckboxList from "@/components/basicWidgets/CheckboxList";
import CheckboxWidget from "@/components/basicWidgets/CheckboxWidget";
import { capitalize } from "@mui/material";

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

const UsageContainer = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: start;
  margin: 3px;
  padding: 10px 30px;
  background: var(--light-gray);
  width: 100%;
  max-height: 200px;
  overflow-y: scroll;
  font-size: 13px;
`;

const UsageLabel = styled.div`
  min-width: 89px;
  margin: 3px 40px;
`;

const ProductLabel = styled.div`
  font-weight: bold;
  margin: 10px 5px 5px 5px;
  font-size: 15px;
`;

const UsageInputContainer = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 280px;
  height: 40px;
  maxheight: 200px;
`;

const ErrorMsg = styled.span`
  color: red;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 85%;
  padding-top: 2%;
`;

export default function EditCustomerForm({ customerData, openEditModal, setOpenEditModal, resetTable }) {
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [productOptions, setProductOptions] = useState([]);
  const [buttons, setButtons] = useState(["Cancel", "Save"]);
  const [labels, setLabels] = useState([]);
  const [usage, setUsage] = useState({});
  const [unlimitedUploads, setUnlimitedUploads] = useState([]);
  const [unlimitedAnalyses, setUnlimitedAnalyses] = useState([]);
  const [errorMsg, setErrorMsg] = useState([]);

  useEffect(() => {
    if (!customerData) {
      return;
    }
    // get available products to choose from
    const parsedCustomerUsage = JSON.parse(customerData.usage);
    setProductOptions(Object.keys(parsedCustomerUsage));

    // set current customer products
    setSelectedProducts(customerData.scopes.map((s) => s.split(":")[0]));

    // set current usage
    setUsage(parsedCustomerUsage);

    // handle unlimited uploads
    const currentUnlimitedUploads = Object.keys(parsedCustomerUsage).filter(
      (p) => parsedCustomerUsage[p].uploads === -1
    );
    setUnlimitedUploads(currentUnlimitedUploads);

    // handle unlimited analyses
    const currentUnlimitedAnalyses = Object.keys(parsedCustomerUsage).filter(
      (p) => parsedCustomerUsage[p].jobs === -1
    );
    setUnlimitedAnalyses(currentUnlimitedAnalyses);

    // ensure the modal resets if error messages were showing
    setLabels([]);
    setButtons(["Cancel", "Save"]);
  }, [customerData]);

  const handleButtonSelection = async (idx) => {
    if (idx === 1) {
      try {
        const usageCopy = JSON.parse(JSON.stringify(usage));
        for (const product in usageCopy) {
          const exp = usageCopy[product].expiration_date;
          if (exp) {
            // check if valid date, also check number of values because new Date('<single int>') has weird behaviors. Enforce xxxx-xx-xx
            // reset labels so the buttons disabled state returns to false and return so request isn't sent
            if (new Date(exp).toString() === "Invalid Date" || exp.split("-").length !== 3) {
              setLabels([]);
              setErrorMsg("*Invalid date format");
              return;
            } else {
              setErrorMsg();
            }
          } else {
            usageCopy[product].expiration_date = null;
          }

          if (unlimitedUploads.includes(product)) {
            usageCopy[product].uploads = -1;
            setErrorMsg();
          } else if (usageCopy[product].uploads < 0) {
            setLabels([]);
            setErrorMsg("*Upload limit must be >= 0");
            return;
          } else {
            setErrorMsg();
          }

          if (unlimitedAnalyses.includes(product)) {
            usageCopy[product].jobs = -1;
            setErrorMsg();
          } else if (usageCopy[product].jobs < 0) {
            setLabels([]);
            setErrorMsg("*Analysis limit must be >= 0");
            return;
          } else {
            setErrorMsg();
          }
        }

        const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/customers/${customerData.id}`, {
          method: "PUT",
          body: JSON.stringify({ usage: usageCopy, products: selectedProducts, action_type: "edit" }),
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

  const handleCheckedState = (product, checked, setter, state) => {
    product = product.toLowerCase();

    if (checked) {
      setter([...state, product]);
    } else {
      state.splice(state.indexOf(product), 1);
      setter([...state]);
    }
  };

  const updateUsageSettings = (value, product, key) => {
    usage[product][key] = value;
    setUsage({ ...usage });
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
      {labels.length === 0 && (
        <>
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
              height="100px"
              width="100%"
              disabled={[false, false]}
              options={productOptions.map((p) => capitalize(p))}
              checkedItems={selectedProducts.map((p) => capitalize(p))}
              setCheckedItems={(item, state) =>
                handleCheckedState(item, state, setSelectedProducts, selectedProducts)
              }
            />
            <StaticLabel style={{ width: "150px" }}>Usage Restrictions:</StaticLabel>
            <UsageContainer>
              {productOptions.map(
                (product) =>
                  selectedProducts.includes(product) && (
                    <div key={product}>
                      <ProductLabel>{capitalize(product)}</ProductLabel>
                      <UsageInputContainer style={{ width: "335px" }}>
                        <UsageLabel>Analyses:</UsageLabel>
                        <FormInput
                          name="num_uploads"
                          placeholder={"10000"}
                          value={unlimitedUploads.includes(product) ? "" : usage[product].uploads}
                          disabled={unlimitedUploads.includes(product)}
                          height="25px"
                          onChangeFn={(e) => {
                            updateUsageSettings(e.target.value, product, "uploads");
                          }}
                        />
                        <CheckboxWidget
                          size={"sm"}
                          checkedState={unlimitedUploads.includes(product)}
                          handleCheckbox={(state) =>
                            handleCheckedState(product, state, setUnlimitedUploads, unlimitedUploads)
                          }
                        />{" "}
                        unlimited
                      </UsageInputContainer>
                      <UsageInputContainer style={{ width: "335px" }}>
                        <UsageLabel>Analyses:</UsageLabel>
                        <FormInput
                          name="num_analyses"
                          placeholder={"10000"}
                          value={unlimitedAnalyses.includes(product) ? "" : usage[product].jobs}
                          disabled={unlimitedAnalyses.includes(product)}
                          height="25px"
                          onChangeFn={(e) => {
                            updateUsageSettings(e.target.value, product, "jobs");
                          }}
                        />
                        <CheckboxWidget
                          size={"sm"}
                          checkedState={unlimitedAnalyses.includes(product)}
                          handleCheckbox={(state) =>
                            handleCheckedState(product, state, setUnlimitedAnalyses, unlimitedAnalyses)
                          }
                        />{" "}
                        unlimited
                      </UsageInputContainer>
                      <UsageInputContainer>
                        <UsageLabel>Expiration (yyyy-mm-dd):</UsageLabel>
                        <FormInput
                          name="expiration"
                          placeholder={"none"}
                          value={usage[product].expiration_date || ""}
                          height="25px"
                          onChangeFn={(e) => {
                            updateUsageSettings(e.target.value, product, "expiration_date");
                          }}
                        />
                      </UsageInputContainer>
                    </div>
                  )
              )}
            </UsageContainer>
            <ErrorMsg>{errorMsg}</ErrorMsg>
          </BodyContainer>
        </>
      )}
    </ModalWidget>
  );
}
