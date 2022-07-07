import { useRouter } from "next/router";
import styled from "styled-components";
import { useEffect, useState, useContext } from "react";
import { AuthContext } from "@/pages/_app";
import ArrowForwardIosSharpIcon from "@mui/icons-material/ArrowForwardIosSharp";
import MuiAccordion, { AccordionProps } from "@mui/material/Accordion";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import MuiAccordionSummary, {
  AccordionSummaryProps,
} from "@mui/material/AccordionSummary";
import MuiAccordionDetails from "@mui/material/AccordionDetails";

const Container = styled.div`
  height: inherit;
  background-color: var(--dark-blue);
  min-width: 200px;
  width: 20%;
  position: relative;
  display: flex;
  flex-direction: column;
`;

const ListItem = styled.li`
  font-size: 15px;
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

const AccordionSummary = styled((AccordionSummaryProps) => (
  <MuiAccordionSummary
    {...AccordionSummaryProps}
    sx={{ color: "var(--light-gray)" }}
  />
))(({ props }) => ({
  flexDirection: "row-reverse",
  backgroundColor: props.color,
  height: "75px",
  "& .MuiAccordionSummary-expandIconWrapper.Mui-expanded": {
    transform: "rotate(90deg)",
    height: "100%",
    paddingRight: "6px",
  },
  "& .MuiAccordionSummary-expandIconWrapper": {
    height: "100%",
  },
  "& .MuiAccordionSummary-content": {
    margin: "0px",
    justifyContent: "center",
    fontSize: "18px",
  },
  "&:hover": {
    backgroundColor: props.disabled ? "var(--dark-blue)" : "var(--teal-green)",
    cursor: props.disabled ? "default" : "pointer",
  },
}));

const AccordionDetails = styled((AccordionDetailsProps) => (
  <MuiAccordionDetails {...AccordionDetailsProps} />
))(() => ({
  backgroundColor: "var(--light-gray)",
}));

export const Accordion = styled((AccordionProps) => (
  <MuiAccordion disableGutters elevation={0} square {...AccordionProps} />
))(() => ({
  position: "unset",
  border: "none",
  boxShadow: "none",
}));

const userButtons = [
  { label: "Home", disabled: false, page: "/uploads", options: [] },
  {
    label: "Run Analysis",
    disabled: false,
    page: "/upload-form",
    options: ["Re-analyze Existing Upload", "Analyze New Files"],
  },
  {
    label: "Account Settings",
    disabled: true,
    page: "/account",
    options: [],
  },
];

const adminButtons = [
  {
    label: "Add New User",
    disabled: false,
    page: "/admin/new-user",
    options: [],
  },
];

export default function ControlPanel() {
  const router = useRouter();
  const [selected, setSelected] = useState("Home");
  const [expanded, setExpanded] = useState(null);
  const { accountType } = useContext(AuthContext);
  const buttons = accountType === "Admin" ? adminButtons : userButtons;

  useEffect(() => {
    const { label, options } = buttons.filter(
      ({ page }) => page === router.pathname
    )[0];

    if (label !== selected) setSelected(label);
    if (options.length > 0) setExpanded(label);
  }, [buttons, router]);

  return (
    <Container>
      {buttons.map(({ disabled, label, page, options }, idx) => {
        const handleListClick = (e) => {
          e.preventDefault();
          router.push({ pathname: page, query: { id: e.target.value } });
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
          selected === label ? "var(--teal-green)" : "var(--dark-blue)";

        return (
          <ThemeProvider
            key={label}
            theme={theme({ color: backgroundColor, disabled })}
          >
            <Accordion disabled={disabled} expanded={expanded === label}>
              <AccordionSummary
                props={{ color: backgroundColor }}
                onClick={handleSelected}
                value={idx}
                expandIcon={
                  options.length > 0 ? (
                    <ArrowForwardIosSharpIcon
                      sx={{
                        fontSize: "0.9rem",
                        position: "relative",
                        color: "var(--light-gray)",
                        marginLeft: "12px",
                        height: "100%",
                      }}
                    />
                  ) : null
                }
              >
                {label}
              </AccordionSummary>
              <AccordionDetails>
                <ListContainer>
                  {options.map((val, idx) => (
                    <ListItem key={val} value={idx} onClick={handleListClick}>
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
  );
}
