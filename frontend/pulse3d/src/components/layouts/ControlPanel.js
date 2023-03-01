import { useRouter } from "next/router";
import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import { AuthContext } from "@/pages/_app";
import ArrowForwardIosSharpIcon from "@mui/icons-material/ArrowForwardIosSharp";
import MuiAccordion from "@mui/material/Accordion";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import MuiAccordionSummary from "@mui/material/AccordionSummary";
import MuiAccordionDetails from "@mui/material/AccordionDetails";
import ModalWidget from "@/components/basicWidgets/ModalWidget";
import { styled as muiStyled } from "@mui/material/styles";

const Container = styled.div`
  height: inherit;
  background-color: var(--dark-blue);
  min-width: 200px;
  width: 15vw;
  position: fixed;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
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
  align-items: center;
  padding: 0;
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

const ArrowIcon = muiStyled(ArrowForwardIosSharpIcon)`
  font-size: 0.9rem;
  position: relative;
  color: var(--light-gray);
  margin-left: 12px;
  height: 100%;
`;

const AccordionSummary = muiStyled(MuiAccordionSummary)`
  flex-direction: row-reverse;
  height: 75px;
  color: var(--light-gray);
  & .MuiAccordionSummary-expandIconWrapper.Mui-expanded {
    transform: rotate(90deg);
    height: 100%;
    padding-right: 6px;
  }
  & .MuiAccordionSummary-expandIconWrapper {
    height: 100%;
  }
  & .MuiAccordionSummary-content {
    margin: 0px;
    justify-content: center;
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

const adminButtons = [
  { label: "Home", disabled: false, page: "/uploads", options: [] },
  {
    label: "Add New User",
    disabled: false,
    page: "/new-user",
    options: [],
  },
  { label: "Users Info", disabled: false, page: "/users-info", options: [] },
];
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
  const { accountType, usageQuota } = useContext(AuthContext);
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });

  const userButtons = [
    { label: "Home", disabled: false, page: "/uploads", options: [] },
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
      options: ["Usage Details"],
      //TODO add notifications page
    },
    { label: "Metric Definitions", options: [] },
  ];

  const buttons = accountType === "admin" ? adminButtons : userButtons;

  useEffect(() => {
    // this checks if a page changes without button is clicked from a forced redirection
    const currentPage = buttons.filter(({ page }) => page === router.pathname)[0];

    if (currentPage) {
      const { label, options } = currentPage;
      if (label !== selected) setSelected(label);
      if (options.length > 0) setExpanded(label);
      else setExpanded(null);
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
        if (usageQuota.jobs_reached) setModalLabels(modalObjs.jobsReached);
        else if (usageQuota.uploads_reached) setModalLabels(modalObjs.uploadsReached);

        setModalState(true);
      }
    }
  }, [usageQuota]);

  return (
    <>
      <Container>
        {buttons.map(({ disabled, label, page, options }, idx) => {
          const handleListClick = (e) => {
            e.preventDefault();
            router.push({ pathname: page, query: { id: e.target.id } });
          };

          const handleSelected = (e) => {
            e.preventDefault();
            //if metric definitions button then open window with metric definitions
            if (label === userButtons[3].label) {
              window.open("https://pulse3d.readthedocs.io/en/latest/_images/twitch_metrics_diagram.png");
              return;
            }
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
