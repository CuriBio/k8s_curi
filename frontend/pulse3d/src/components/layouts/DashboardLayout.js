import ControlPanel from "@/components/layouts/ControlPanel";
import { useEffect, useState, createContext } from "react";
import styled from "styled-components";
import { useRouter } from "next/router";
import semverRsort from "semver/functions/rsort";

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
  const [pulse3dVersions, setPulse3dVersions] = useState([]);
  const [metaPulse3dVersions, setMetaPulse3dVersions] = useState([]);
  const router = useRouter();

  useEffect(() => {
    if (router.pathname === "/uploads") {
      getUploads();
      getPulse3dVersions();
    } else if (router.pathname === "/upload-form") {
      getPulse3dVersions();
    }
  }, [router.pathname, fetchUploads]);

  const getUploads = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads`);

      if (response && response.status === 200) {
        const uploadsArr = await response.json();
        setUploads(uploadsArr);
      }
    } catch (e) {
      console.log("ERROR getting uploads for user");
    }
  };

  // when page loads, get all available pulse3d versions
  async function getPulse3dVersions() {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_PULSE3D_URL}/versions`);
      // sort in desc order so that the latest version shows up first
      const versions = await response.json();
      setMetaPulse3dVersions(versions); // keep track of states

      const testingVersions = versions.filter(({ state }) => state === "testing");
      const externalVersions = versions.filter(({ state }) => state === "external");

      // sort versions in testing state and add [testing] tag to UI
      // testing versions only to be used in test cluster
      const sortedTestingVersions = semverRsort(testingVersions.map(({ version }) => version));
      // sort versions in external state, no tag required
      const sortedExternalVersions = semverRsort(externalVersions.map(({ version }) => version));

      if (process.env.NEXT_PUBLIC_CLUSTER === "test") {
        setPulse3dVersions([...sortedExternalVersions, ...sortedTestingVersions]);
      } else {
        setPulse3dVersions(sortedExternalVersions);
      }
    } catch (e) {
      console.log(`ERROR getting pulse3d versions: ${e}`);
    }
  }

  return (
    <UploadsContext.Provider
      value={{ uploads, setUploads, setFetchUploads, pulse3dVersions, metaPulse3dVersions }}
    >
      <Container>
        <ControlPanel />
        {children}
      </Container>
    </UploadsContext.Provider>
  );
}
