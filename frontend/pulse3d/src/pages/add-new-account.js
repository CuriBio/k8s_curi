import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import NewAccountForm from "@/components/admin/NewAccountForm";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";

// TODO eventually need to find a better to way to handle some of these globally to use across app
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  align-items: center;
  height: 100%;
  flex-direction: column;
`;

export default function AddNewAccount() {
  const router = useRouter();
  const [newAccountType, setNewAccountType] = useState("user");

  useEffect(() => {
    setNewAccountType(router.query.id);
  }, [router.query]);

  return (
    <BackgroundContainer>
      <NewAccountForm type={newAccountType} />
    </BackgroundContainer>
  );
}

AddNewAccount.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
