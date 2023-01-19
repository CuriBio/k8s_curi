import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  align-items: center;
  height: 100%;
  width: 85%;
  flex-direction: column;
`;

export default function AccountSettings() {
  return (
    <BackgroundContainer>
      <div>Hello</div>
    </BackgroundContainer>
  );
}

AccountSettings.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
