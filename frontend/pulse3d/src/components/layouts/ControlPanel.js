import { useRouter } from "next/router";
import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import { AuthContext } from "@/pages/_app";
import NavigateBeforeIcon from "@mui/icons-material/NavigateBefore";
import MuiAccordion from "@mui/material/Accordion";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import MuiAccordionSummary from "@mui/material/AccordionSummary";
import MuiAccordionDetails from "@mui/material/AccordionDetails";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import { styled as muiStyled } from "@mui/material/styles";

const Container = styled.div`
  height: inherit;
  background-color: var(--dark-blue);
  min-width: 240px;
  width: 15vw;
  position: fixed;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  z-index: 2;
  border-right: 1px solid var(--dark-gray);
`;

const ListItem = styled.li`
  font-size: 15px;
  text-align: center;
  &:hover {
    color: var(--light-blue);
    text-decoration: underline;
    cursor: pointer;
  }
`;

const ListContainer = styled.ul`
  list-style-type: none;
  line-height: 3;
  display: flex;
  flex-direction: column;
  align-items: start;
  padding-left: 10px;
`;

// this is the best way to target and override style props of child components used in other MUI components
const theme = ({ color }) => {
  return createTheme({
    components: {
      MuiButtonBase: {
        styleOverrides: {
          root: {
            padding: "0px",
            backgroundColor: color,
          },
        },
      },
    },
  });
};

const ArrowIcon = muiStyled(NavigateBeforeIcon)`
  font-size: 25px;
  position: relative;
  color: var(--light-gray);
  margin-left: 12px;
  height: 100%;
`;

const AccordionSummary = muiStyled(MuiAccordionSummary)`
  height: 75px;
  color: var(--light-gray);

  & .MuiAccordionSummary-expandIconWrapper.Mui-expanded {
    transform: rotate(90deg);
    height: 100%;
    margin-bottom: 23px;
  }
  & .MuiAccordionSummary-expandIconWrapper {
    height: 100%;
    transform: rotate(-90deg);
    margin-top: 13px;
  }
  & .MuiAccordionSummary-content {
    margin: 0px 15px;
    justify-content: left;
    display: flex;
    font-size: 18px;
  }
`;

const AccordionDetails = muiStyled(MuiAccordionDetails)`
  background: var(--light-gray);
`;

const Accordion = muiStyled(MuiAccordion)`
  position: unset;
  border: none;
  box-shadow: none;
`;

const modalObjs = {
  jobsReached: {
    header: "Warning!",
    messages: [
      "All usage limits have been reached for this customer account.",
      "Users will not be able to upload new recording files or perform re-analysis on existing files.",
    ],
  },
  uploadsReached: {
    header: "Warning!",
    messages: [
      "The upload limit has been reached for this customer account.",
      "Users will only be allowed to perform re-analysis on existing files.",
    ],
  },
};

export default function ControlPanel() {
  const router = useRouter();
  const [selected, setSelected] = useState(router.pathname.replace("-", " ").replace("/", ""));
  const [expanded, setExpanded] = useState(null);
  const { accountType, usageQuota, accountScope, isCuriAdmin } = useContext(AuthContext);
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });

  const userButtons = [
    { label: "Uploads", disabled: false, page: "/uploads", options: [] },
    {
      label: "Run Analysis",
      disabled: usageQuota && usageQuota.jobs_reached, // disabled completely if jobs quota has been reached
      page: "/upload-form",
      options:
        usageQuota && usageQuota.uploads_reached // prevent new analyses if uploads quota reached
          ? ["Re-analyze Existing Upload"]
          : ["Analyze New Files", "Re-analyze Existing Upload"],
    },
    {
      label: "Account Settings",
      page: "/account-settings",
      options: [],
    },
    { label: "Metric Definitions", page: "/metrics", options: [] },
  ];

  const adminButtons = [
    { label: "Uploads", disabled: false, page: "/uploads", options: [] },
    {
      label: "Add New",
      disabled: false,
      page: "/add-new-account",
      options: ["User"],
    },
    { label: "Users Info", disabled: false, page: "/users-info", options: [] },
    {
      label: "Account Settings",
      disabled: false,
      page: "/account-settings",
      options: [],
    },
  ];

  const panelButtons = accountType === "admin" ? adminButtons : userButtons;
  const productionConsoleOptions = [];
  const mantarrayProductionScopes = ["mantarray:serial_number:edit", "mantarray:firmware:edit"];

  if (accountScope) {
    // will have other pages that will be conditionally available depending on scope in the future
    if (accountScope.some((scope) => mantarrayProductionScopes.includes(scope))) {
      productionConsoleOptions.push("Mantarray");
    }

    if (productionConsoleOptions.length > 0) {
      panelButtons.push({
        label: "Production Console",
        page: "/production-console",
        options: productionConsoleOptions,
      });
    }
  }

  if (isCuriAdmin) {
    // if the curi admin acccount is logged in, allow them to add new customers
    adminButtons[1].options.push("Customer");
  }

  useEffect(() => {
    // this checks if a page changes without button is clicked from a forced redirection
    const currentPage = panelButtons.filter(({ page }) => page === router.pathname)[0];

    if (currentPage) {
      const { label, options } = currentPage;

      if (label !== selected) {
        setSelected(label);
      }

      setExpanded(options.length > 0 ? label : null);
    }
  }, [router]);

  useEffect(() => {
    if (usageQuota) {
      // the query param is the only way to check if a user has just logged in versus refreshing the page
      const userJustLoggedIn = router.query.checkUsage && router.pathname === "/uploads";
      // modal will open for admin and user accounts to notify them
      // only open modal if one of the restrictions has been reached
      if ((usageQuota.jobs_reached || usageQuota.uploads_reached) && userJustLoggedIn) {
        // setting local state to compare against when it changes during a session to pop up new modal
        // if jobs are reached, then all uploading/analyses will be disabled
        // else if just uploads are reached, user can still perform re-analysis
        if (usageQuota.jobs_reached) {
          setModalLabels(modalObjs.jobsReached);
        } else if (usageQuota.uploads_reached) {
          setModalLabels(modalObjs.uploadsReached);
        }

        setModalState(true);

        // reset query param so that userJustLoggedIn becomes false
        router.replace("/uploads", undefined, { shallow: true });
      }
    }
  }, [usageQuota]);

  return (
    <>
      <Container>
        {panelButtons.map(({ disabled, label, page, options }, idx) => {
          const handleListClick = (e) => {
            e.preventDefault();
            console.log("here");
            router.push({ pathname: page, query: { id: e.target.id.toLowerCase() } });
          };

          const handleSelected = (e) => {
            e.preventDefault();
            setSelected(label);

            if (options.length === 0) {
              router.push(page);
              setExpanded(null);
            } else {
              setExpanded(expanded === label ? null : label);
            }
          };

          let backgroundColor =
            selected.toLocaleLowerCase() === label.toLowerCase() ? "var(--teal-green)" : "var(--dark-blue)";

          return (
            <ThemeProvider key={label} theme={theme({ color: backgroundColor, disabled })}>
              <Accordion
                disableGutters
                elevation={0}
                square
                disabled={disabled}
                expanded={expanded === label}
              >
                <AccordionSummary
                  sx={{
                    backgroundColor,
                    ":hover": {
                      background: disabled ? "var(--dark-blue)" : "var(--teal-green)",
                      cursor: disabled ? "default" : "pointer",
                    },
                  }}
                  onClick={handleSelected}
                  value={idx}
                  expandIcon={options.length > 0 ? <ArrowIcon /> : null}
                >
                  {label}
                </AccordionSummary>
                <AccordionDetails>
                  <ListContainer>
                    {options.map((val) => (
                      <ListItem key={val} id={val} onClick={handleListClick}>
                        {val}
                      </ListItem>
                    ))}
                  </ListContainer>
                </AccordionDetails>
              </Accordion>
            </ThemeProvider>
          );
        })}
      </Container>
      <ModalWidget
        open={modalState}
        labels={modalLabels.messages}
        closeModal={() => setModalState(false)}
        header={modalLabels.header}
      />
    </>
  );
}
