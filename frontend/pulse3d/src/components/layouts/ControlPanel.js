import { useRouter } from "next/router";
import styled from "styled-components";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import { useEffect, useState } from "react";
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
  <MuiAccordionSummary {...AccordionSummaryProps} />
))(({ props }) => ({
  flexDirection: "row-reverse",
  backgroundColor: props.color,
  "& .MuiAccordionSummary-expandIconWrapper.Mui-expanded": {
    transform: "rotate(90deg)",
    height: "100%",
  },
  "& .MuiAccordionSummary-expandIconWrapper": {
    height: "100%",
  },
  "& .MuiAccordionSummary-content": {
    margin: "0px",
  },
  "&:hover": {
    backgroundColor: props.disabled ? "var(--dark-blue)" : "var(--teal-green)",
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

export default function ControlPanel() {
  const router = useRouter();
  const [selected, setSelected] = useState("Home");
  const [expanded, setExpanded] = useState(null);
  const buttons = [
    { label: "Home", disabled: false, page: "/uploads", options: [] },
    {
      label: "Run Analysis",
      disabled: false,
      page: "/uploadForm",
      options: ["Re-analyze Existing Upload", "Analyze New Files"],
    },
    {
      label: "Account Settings",
      disabled: true,
      page: "/account",
      options: [],
    },
  ];

  useEffect(() => {
    // corrects selected button when user navigates with back/forward button
    const { label, options } = buttons.filter(
      ({ page }) => page === router.pathname
    )[0];

    if (label !== selected) setSelected(label);
    if (options.length > 0) setExpanded(label);
  }, [router]);

  return (
    <Container>
      {buttons.map(({ label, disabled, page, options }) => {
        const handleSelected = (val) => {
          setSelected(val);

          if (options.length === 0) {
            router.push(page);
            setExpanded(null);
          } else {
            setExpanded(expanded === val ? null : val);
          }
        };

        const handleListClick = (e) => {
          e.preventDefault();

          router.push({ pathname: page, query: { id: e.target.value } });
        };

        let backgroundColor =
          selected === label ? "var(--teal-green)" : "var(--dark-blue)";

        return (
          <ThemeProvider key={label} theme={theme({ color: backgroundColor })}>
            <Accordion expanded={expanded === label}>
              <AccordionSummary
                aria-controls={`${label}-content`}
                id={`${label}-button`}
                props={{ color: backgroundColor, disabled }}
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
                <ButtonWidget
                  key={label}
                  height={"65px"}
                  label={label}
                  clickFn={handleSelected}
                  isSelected={selected === label}
                  disabled={disabled}
                  backgroundColor={backgroundColor}
                />
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
