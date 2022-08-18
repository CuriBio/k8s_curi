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
  const [fetchUploads, setFetchUploads] = useState(false);
  const { accountType } = useContext(AuthContext);
  const router = useRouter();

  useEffect(() => {
    if (accountType && accountType !== "Admin") getUploads();
    else if (accountType === null)
      // will return null if reset in the ServiceWorker, undefined if ServiceWorker hasn't responded yet on refresh
      router.replace("/login", null, { shallow: true });
  }, [router, accountType, fetchUploads]);

  const getUploads = async () => {
    try {
      const response = await fetch("https://curibio.com/uploads");

      if (response && response.status === 200) {
        const uploadsArr = await response.json();
        setUploads(uploadsArr);
      }
    } catch (e) {
      console.log("ERROR getting uploads for user");
    }
  };

  return (
    <UploadsContext.Provider value={{ uploads, setUploads, setFetchUploads }}>
      <Container>
        <ControlPanel />
        {children}
      </Container>
    </UploadsContext.Provider>
  );
}
