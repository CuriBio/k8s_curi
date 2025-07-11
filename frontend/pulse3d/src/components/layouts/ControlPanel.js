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
import VersionWidget from "@/components/basicWidgets/VersionWidget";
import { UploadsContext } from "@/pages/_app";

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

const VersionContainer = styled.div`
  width: 100%;
  position: relative;
  display: flex;
  justify-content: center;
  height: 100px;
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
  deprecationWarning: {
    header: "Action Required!",
    messages: ["Your preferred Pulse3D version is now deprecated.", "Please select another version:"],
  },
};

const getUserButtons = (productPage, usageQuota) => {
  if (["mantarray", "nautilai"].includes(productPage)) {
    return [
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
      { label: "Metric Definitions", page: "/metrics", options: ["V0-V1", "V2"] },
    ];
  } else if (productPage === "advanced_analysis") {
    return [
      { label: "Analyses", disabled: false, page: "/advanced-analyses", options: [] },
      {
        label: "Run Analysis",
        disabled: usageQuota && usageQuota.jobs_reached, // disabled completely if jobs quota has been reached
        page: "/advanced-analysis-form",
        options: [],
      },
      {
        label: "Account Settings",
        page: "/account-settings",
        options: [],
      },
    ];
  } else {
    return [];
  }
};

export default function ControlPanel() {
  const router = useRouter();
  const { accountType, usageQuota, accountScope, isCuriAdmin, preferences, productPage } = useContext(
    AuthContext
  );
  const { pulse3dVersions, metaPulse3dVersions } = useContext(UploadsContext);
  const [selected, setSelected] = useState(router.pathname.replace("-", " ").replace("/", ""));
  const [expanded, setExpanded] = useState(null);
  const [modalState, setModalState] = useState(false);
  const [modalLabels, setModalLabels] = useState({ header: "", messages: [] });
  const [deprecationModalState, setDeprecationModalState] = useState(false);
  const [selectedP3dVersion, setSelectedP3dVersion] = useState(0);

  const userButtons = getUserButtons(productPage, usageQuota);

  const adminButtons = [
    { label: "Uploads", disabled: false, page: "/uploads", options: [] },
    {
      label: "Add New",
      disabled: false,
      page: "/add-new-account",
      options: ["User"],
    },
    { label: "User Info", disabled: false, page: "/user-info", options: [] },
    {
      label: "Account Settings",
      disabled: false,
      page: "/account-settings",
      options: [],
    },
  ];

  const panelButtons = accountType === "admin" ? adminButtons : userButtons;

  const productionScopes = {
    mantarray: [
      "mantarray:serial_number:list",
      "mantarray:serial_number:edit",
      "mantarray:firmware:edit",
      "mantarray:firmware:list",
    ],
    // Tanner (4/4/24): currently no production scopes for nautilai
    nautilai: [],
  };

  if (accountScope?.some((scope) => productionScopes[productPage]?.includes(scope))) {
    // will have other pages that will be conditionally available depending on scope in the future
    panelButtons.push({
      label: "Production Console",
      page: "/production-console",
      options: [],
    });
  }

  if (isCuriAdmin) {
    // if the curi admin acccount is logged in, allow them to add new admins
    adminButtons[1].options.push("Admin");
    adminButtons.splice(
      3,
      0,
      {
        label: "Customer Info",
        disabled: false,
        page: "/customer-info",
        options: [],
      },
      {
        label: "Notifications",
        disabled: false,
        page: "/notifications-management",
        options: [],
      }
    );
  }

  useEffect(() => {
    // this checks if a page changes without button is clicked from a forced redirection
    // this also deselects panel buttons if an option outside the panel is clicked (e.g. notifications in the top right)
    const currentPage = panelButtons.filter(({ page }) => page === router.pathname)[0];

    if (currentPage) {
      const { label, options } = currentPage;

      if (label !== selected) {
        setSelected(label);
      }

      setExpanded(options.length > 0 ? label : null);
    } else {
      setSelected("");
      setExpanded(null);
    }
  }, [router]);

  useEffect(() => {
    if (preferences?.[productPage]?.version != null && pulse3dVersions.length > 0) {
      checkVersionDeprecation();
    }
  }, [pulse3dVersions]);

  useEffect(() => {
    if (!usageQuota) {
      return;
    }

    const homepage = userButtons[0]?.page || "/uploads";
    // the query param is the only way to check if a user has just logged in versus refreshing the page
    const userJustLoggedIn = router.query.checkUsage && router.pathname === homepage;
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
      router.replace(homepage, undefined, { shallow: true });
    }
  }, [usageQuota]);

  const handleDeprecationClose = async (_) => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/preferences`, {
        method: "PUT",
        body: JSON.stringify({
          product: productPage,
          changes: { version: pulse3dVersions[selectedP3dVersion] },
        }),
      });
      setDeprecationModalState(false);
    } catch (e) {
      console.log("ERROR updating user preferences");
    }
  };

  const checkVersionDeprecation = () => {
    const selectedVersionMeta = metaPulse3dVersions.find(
      (m) => preferences?.[productPage]?.version === m.version
    );

    // deprecated versions are filtered out in DashboardLayout
    if (!selectedVersionMeta || selectedVersionMeta.state === "deprecated") {
      setDeprecationModalState(true);
    }
  };

  return (
    <>
      <Container>
        {panelButtons.map(({ disabled, label, page, options }, idx) => {
          const handleListClick = (e) => {
            e.preventDefault();
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
      <ModalWidget
        open={deprecationModalState}
        labels={modalObjs.deprecationWarning.messages}
        closeModal={handleDeprecationClose}
        buttons={["Save"]}
        header={modalObjs.deprecationWarning.header}
      >
        <VersionContainer>
          <VersionWidget
            selectedP3dVersion={selectedP3dVersion}
            setSelectedP3dVersion={setSelectedP3dVersion}
          />
        </VersionContainer>
      </ModalWidget>
    </>
  );
}
