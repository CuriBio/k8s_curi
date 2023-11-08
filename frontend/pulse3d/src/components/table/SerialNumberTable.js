import { useState, useEffect } from "react";
import styled from "styled-components";
import FormInput from "@/components/basicWidgets/FormInput";
import semverValid from "semver/functions/valid";

const SubContainer = styled.div`
  width: 60%;
  display: flex;
  align-items: center;
  background-color: white;
  border-bottom: 2px solid black;
  border-inline: 2px solid black;
`;

const SubHeader = styled.div`
  width: 60%;
  background-color: var(--dark-blue);
  color: white;
  padding: 0.4rem 0;
  font-size: 0.85rem;
  border-radius: 3px;
  display: flex;
`;

const Header = styled.div`
  width: 33%;
  padding-left: 7px;
`;

const SubRow = styled.div`
  font-size: 0.75rem;
  width: 33%;
  padding: 7px;
  overflow: hidden;
`;

const ActionText = styled.div`
  font-style: italic;

  &:hover {
    color: var(--teal-green);
    text-decoration: underline;
    cursor: pointer;
  }
`;

const DisabledActionText = styled.div`
  font-style: italic;
  color: gray;
`;

export default function SerialNumberTable() {
  const [entries, setEntries] = useState([]);
  const [addingEntry, setAddingEntry] = useState(false);
  const [newEntry, setNewEntry] = useState({});

  const entryIsValid = Boolean(newEntry.serialNumber) && semverValid(newEntry.hardwareVersion);
  const SaveButtonText = entryIsValid ? ActionText : DisabledActionText;

  const getSerialNumbers = async () => {
    const getSerialNumRes = await fetch(`${process.env.NEXT_PUBLIC_MANTARRAY_URL}/serial-number`);
    const getSerialNumResJson = await getSerialNumRes.json();
    const fetchedEntries = getSerialNumResJson.units.map(({ serial_number, hw_version }) => {
      return {
        serialNumber: serial_number,
        hardwareVersion: hw_version,
      };
    });
    setEntries(fetchedEntries);
  };

  // When component first loads, get all serial numbers
  useEffect(() => {
    getSerialNumbers();
  }, []);

  const deleteEntry = async (serialNumber) => {
    await fetch(`${process.env.NEXT_PUBLIC_MANTARRAY_URL}/serial-number/${serialNumber}`, {
      method: "DELETE",
    });
    // update serial numbers after prev request
    await getSerialNumbers();
  };

  const finishEntry = async (save) => {
    if (save) {
      if (!entryIsValid) {
        // If entry is invalid then don't do anything
        return;
      }
      await fetch(`${process.env.NEXT_PUBLIC_MANTARRAY_URL}/serial-number`, {
        method: "POST",
        body: JSON.stringify({ serial_number: newEntry.serialNumber, hw_version: newEntry.hardwareVersion }),
      });
      // update serial numbers after prev request
      await getSerialNumbers();
    }
    setAddingEntry(false);
    setNewEntry({});
  };

  const rows = entries.map(({ serialNumber, hardwareVersion }, i) => {
    return (
      <SubContainer key={`SerialNumberSubcontainer${i}`}>
        <SubRow>{serialNumber}</SubRow>
        <SubRow>{hardwareVersion}</SubRow>
        <SubRow>
          <ActionText
            style={{ textAlign: "right", paddingRight: "20px" }}
            onClick={() => deleteEntry(serialNumber)}
          >
            Delete
          </ActionText>
        </SubRow>
      </SubContainer>
    );
  });

  rows.push(
    <SubContainer key="FinalRow">
      {addingEntry ? (
        <>
          <SubRow>
            <FormInput
              name="serialNumber"
              placeholder="Enter Serial Number"
              value={newEntry.serialNumber || ""}
              onChangeFn={(e) => {
                setNewEntry({
                  ...newEntry,
                  serialNumber: e.target.value,
                });
              }}
            />
          </SubRow>
          <SubRow>
            <FormInput
              name="hardwareVersion"
              placeholder="Enter Hardware Version"
              value={newEntry.hardwareVersion || ""}
              onChangeFn={(e) => {
                setNewEntry({
                  ...newEntry,
                  hardwareVersion: e.target.value,
                });
              }}
            />
          </SubRow>
          <SubRow
            style={{ display: "flex", flexDirection: "row", justifyContent: "right", paddingRight: "30px" }}
          >
            <ActionText style={{ paddingLeft: "20px" }} onClick={() => finishEntry(false)}>
              Cancel
            </ActionText>
            <SaveButtonText style={{ paddingLeft: "20px" }} onClick={() => finishEntry(true)}>
              Save
            </SaveButtonText>
          </SubRow>
        </>
      ) : (
        <SubRow>
          <ActionText style={{ paddingLeft: "20px" }} onClick={() => setAddingEntry(true)}>
            Add Serial Number
          </ActionText>
        </SubRow>
      )}
    </SubContainer>
  );

  return (
    <>
      <SubHeader>
        <Header>Serial Number</Header>
        <Header>Hardware Version</Header>
        <Header />
      </SubHeader>
      {rows}
    </>
  );
}
