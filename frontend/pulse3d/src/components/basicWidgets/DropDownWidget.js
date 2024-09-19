import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import { useEffect, useState } from "react";
import styled from "styled-components";
import OutlinedInput from "@mui/material/OutlinedInput";
import Tooltip from "@mui/material/Tooltip";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { styled as muiStyled } from "@mui/material/styles";

const ErrorText = styled.span`
  color: red;
  padding-left: 15px;
  font-style: italic;
  text-align: left;
  position: relative;
  width: 80%;
  font-size: 16px;
`;

const Placeholder = styled.em`
  font-size: 16px;
  font-weight: bolder;
`;

const ListItem = muiStyled(MenuItem)`
  font-size: 15px;
  padding: 10px 30px;
  font-family: Mulish;
  :hover {
    background: var(--light-gray);
  }
  &.Mui-selected {
    background: white;
  }
`;

const ListText = styled.div`
  width: 100%;
  overflow: hidden;
`;

const DeleteButton = styled.button`
  border: none;
  background-color: var(--dark-grey);
  font-style: italic;

  &:hover {
    color: var(--teal-green);
    text-decoration: underline;
    cursor: pointer;
  }
`;

const AccordionTab = muiStyled(AccordionSummary)`
  font-size: 15px;
  &.MuiAccordionSummary-root.Mui-expanded {
    min-height: 0px;
    height: 42px;
  }
  &.MuiAccordionSummary-root {
    min-height: 0px;
    height: 42px;
    padding: 0px 30px;
  }
  :hover {
    background: var(--light-gray)
  }
  &.MuiAccordionSummary-content {
    margin: 11px 15px;
  },
`;

const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: "400px",
      width: "inherit",
    },
  },
};

const TooltipText = styled.span`
  font-size: 15px;
`;

export default function DropDownWidget({
  options,
  subOptions = {},
  label,
  error = "",
  handleSelection,
  handleDeletion = null,
  reset,
  disabled = false,
  disableOptions = Array(options.length).fill(false),
  optionsTooltipText,
  initialSelected,
  handleSubSelection,
  disableSubOptions = {},
  subOptionsTooltipText = [],
  height = 40,
  setReset,
  boxShadow = "rgba(0, 0, 0, 0.1) 1px 1px 1px 0px, rgba(0, 0, 0, 0.12) 1px 1px 3px 2px",
}) {
  const [selected, setSelected] = useState("");
  const [errorMsg, setErrorMsg] = useState(error);
  const [open, setOpen] = useState(false);

  const handleChange = (idx) => {
    if (!disableOptions[idx]) {
      setSelected(idx);
      setErrorMsg("");
      handleSelection(idx);
    }
  };

  const handleDropdownChange = (e) => {
    // only trigger selection if selected option is not an accordion button because that should just open sub menu, not use as actual selection
    if (!subOptions[options[e.target.value]]) {
      handleChange(e.target.value);
    }
  };

  useEffect(() => {
    // initialSelected needs to be the index of item
    if (initialSelected != null) {
      handleChange(initialSelected);
    }
  }, [initialSelected]);

  useEffect(() => {
    /*
     Sensitive function, this was added to control opening and closing of popup dropdown so that opening an accordion-style item doesn't auto close the dropdown. Material UI applies a modal backdrop that prevents ability to use a ClickAwayListener so applying click event to window and removing when closed.
    */
    if (window !== undefined) {
      if (open) window.addEventListener("click", handleDropdownState);
    }

    return () => window.removeEventListener("click", handleDropdownState);
  }, [open]);

  useEffect(() => {
    if (reset) {
      setSelected(initialSelected != null ? initialSelected : "");
    }
  }, [reset]);
  // TODO 10/11/2022  Should find a better way to handle the opening and closing of the dropdowns instead of handling all click events
  const handleDropdownState = (e) => {
    const option = e.target.innerText;
    if (subOptions[option] && !disableOptions[options.indexOf(option)]) {
      setSelected(options.indexOf(option));
    } else {
      /* Clicking on the select-dropdown, the placeholder text, or the drop arrow to open will trigger this event and without this check, it will auto close and prevent dropdown from ever opening. If user selects outside these components, then we want to close the modal */
      if (!["placeholder-text", "select-dropdown", "dropdown-arrow-icon"].includes(e.target.id)) {
        setOpen(false);
      }
      // reset dropdown if user clicks outside of dropdown, mui adds a backdrop component that takes up entire view so any clicking will reset
      // if setReset is not passed down, then it signals not to reset on clicking away
      // this is important for accordion tab selections
      if (
        setReset &&
        e.target.className &&
        (e.target.id == "dropdown-arrow-icon" || e.target.className.includes("MuiBackdrop-root"))
      )
        setReset(true);
    }
  };

  const handleSubChange = (optionName, subOptionIdx) => {
    handleSubSelection({ optionName, subOptionIdx });
  };

  const getDisabledListItem = (tooltipOptions, idx, item) => {
    return (
      <Tooltip
        placement="left"
        key={idx}
        title={<TooltipText>{tooltipOptions[idx]}</TooltipText>}
        value={idx}
      >
        <div>
          <ListItem disabled={true}>{item}</ListItem>
        </div>
      </Tooltip>
    );
  };

  return (
    <FormControl
      fullWidth
      disabled={disabled}
      onClick={() => {
        if (!disabled) setOpen(true);
      }}
      sx={{
        boxShadow,
      }}
    >
      <Select
        displayEmpty
        labelId="select-label"
        id="select-dropdown"
        input={<OutlinedInput sx={{ height: `${height}px` }} />}
        MenuProps={MenuProps}
        onChange={handleDropdownChange}
        open={open}
        value={options[selected] ? selected : ""}
        renderValue={(selected) => {
          /*
             Must be initialSelected === undefined and not !initialSelected,
             An index of 0 will pass !initialSelected as truthy
          */
          if (selected.length === 0 && initialSelected === undefined) {
            return (
              <Placeholder
                id="placeholder-text"
                onClick={(e) => {
                  e.preventDefault();
                  setOpen(true);
                }}
              >
                {label}
              </Placeholder>
            );
          } else if (selected === "" && initialSelected !== undefined) {
            return options[initialSelected];
          } else {
            return options[selected];
          }
        }}
      >
        <MenuItem disabled>
          <Placeholder>{label}</Placeholder>
        </MenuItem>

        {options.map((item, idx) => {
          // if parent option item is disabled, just return disabled list item with tooltip
          if (disableOptions[idx]) {
            return getDisabledListItem(optionsTooltipText, idx, item);
          } else if (subOptions[item] && subOptions[item].length > 0) {
            // if the parent option has sub menu with more options
            return (
              <Accordion key={idx} value={idx} onClick={() => setSelected(idx)}>
                <AccordionTab
                  expandIcon={
                    <ExpandMoreIcon
                      id="dropdown-arrow-icon"
                      onClick={(e) => {
                        e.preventDefault();
                        setSelected(idx);
                      }}
                    />
                  }
                  id={`${item}-dropdown`}
                >
                  {item}
                </AccordionTab>
                <AccordionDetails>
                  {subOptions[item].map((option, idx) => {
                    // if sub menu item is disabled, return disabled list item with tooltip
                    if (disableSubOptions[item][idx]) {
                      return getDisabledListItem(subOptionsTooltipText[item], idx, option);
                    } else
                      return (
                        <ListItem
                          key={idx}
                          value={idx}
                          onClick={(e) => {
                            e.preventDefault();
                            handleSubChange(item, idx);
                          }}
                        >
                          {option}
                        </ListItem>
                      );
                  })}
                </AccordionDetails>
              </Accordion>
            );
          } else {
            return (
              <ListItem key={idx} value={idx}>
                <ListText>{item}</ListText>
                {handleDeletion != null && (
                  <DeleteButton
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      handleDeletion(idx);
                    }}
                  >
                    Delete
                  </DeleteButton>
                )}
              </ListItem>
            );
          }
        })}
      </Select>
      <ErrorText>{errorMsg}</ErrorText>
    </FormControl>
  );
}
