import { useRouter } from "next/router";
import styled from "styled-components";
import ButtonWidget from "@/components/basicWidgets/ButtonWidget";
import { useEffect, useState } from "react";

const Container = styled.div`
  height: inherit;
  background-color: var(--dark-blue);
  min-width: 200px;
  width: 20%;
  position: relative;
  display: flex;
  flex-direction: column;
`;

export default function ControlPanel() {
  const router = useRouter();
  const [selected, setSelected] = useState("Home");
  const buttons = [
    { label: "Home", disabled: false, page: "/uploads" },
    {
      label: "Start New Analysis",
      disabled: false,
      page: "/uploadForm",
    },
    {
      label: "Account Settings",
      disabled: true,
      page: "/account",
    },
  ];

  useEffect(() => {
    // corrects selected button when user navigates with back/forward button
    const selectedButton = buttons.filter(
      ({ page }) => page === router.pathname
    )[0];
    if (selectedButton.label !== selected) setSelected(selectedButton.label);
  }, [router]);

  return (
    <Container>
      {buttons.map(({ label, disabled, page, as }) => {
        const handleSelected = (value) => {
          setSelected(value);
          router.push(page);
        };

        return (
          <ButtonWidget
            key={label}
            height={"65px"}
            width={"100%"}
            label={label}
            clickFn={handleSelected}
            isSelected={selected === label}
            disabled={disabled}
          />
        );
      })}
    </Container>
  );
}
