import ControlPanel from "@/components/layouts/ControlPanel";
import { useEffect, useState, createContext } from "react";
import styled from "styled-components";
import { useRouter } from "next/router";
const Container = styled.div`
  height: inherit;
  background-color: var(--light-gray);
  width: 100%;
  display: flex;
`;

export const UploadsContext = createContext();

export default function DashboardLayout({ children }) {
  const [uploads, setUploads] = useState([]);
  const router = useRouter();

  useEffect(() => {
    getUploads();
  }, []);

  const getUploads = async () => {
    const response = await fetch("http://localhost/uploads");

    if (response && response.status === 200) {
      const uploadsArr = await response.json();
      setUploads(uploadsArr);
    } else if (response && [403, 401].includes(response.status)) {
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
