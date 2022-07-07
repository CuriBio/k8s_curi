import ControlPanel from "@/components/layouts/ControlPanel";
import { useEffect, useState, createContext, useContext } from "react";
import styled from "styled-components";
import { useRouter } from "next/router";
import { AuthContext } from "@/pages/_app";

const Container = styled.div`
  height: inherit;
  background-color: var(--light-gray);
  width: 100%;
  display: flex;
`;

export const UploadsContext = createContext();

export default function DashboardLayout({ children }) {
  const [uploads, setUploads] = useState([]);
  const { accountType } = useContext(AuthContext);
  const router = useRouter();

  useEffect(() => {
    if (accountType && accountType !== "Admin") getUploads();
  }, [accountType]);

  const getUploads = async () => {
    const response = await fetch("http://localhost/uploads");

    if (response && response.status === 200) {
      const uploadsArr = await response.json();
      setUploads(uploadsArr);
    } else if (response && response.status === 401 && accountType) {
      router.replace("/login", null, { shallow: true });
    }
  };

  return (
    <UploadsContext.Provider value={{ uploads }}>
      <Container>
        <ControlPanel />
        {children}
      </Container>
    </UploadsContext.Provider>
  );
}
