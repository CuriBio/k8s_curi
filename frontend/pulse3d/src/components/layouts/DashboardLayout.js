import ControlPanel from "@/components/layouts/ControlPanel";
import { useEffect, useState, createContext, useContext } from "react";
import styled from "styled-components";
import { useRouter } from "next/router";
import semverRsort from "semver/functions/rsort";
import { AuthContext } from "@/pages/_app";

const Container = styled.div`
  height: inherit;
  background-color: var(--light-gray);
  width: 100%;
  display: flex;
  top: 65px;
  position: absolute;
  overflow-x: hidden;
`;

const PageContainer = styled.div`
  margin-left: max(15%, 240px);
  width: 85%;
  min-height: 95vh;
`;

export const UploadsContext = createContext();

export default function DashboardLayout({ children }) {
  const [uploads, setUploads] = useState();
  const [fetchUploads, setFetchUploads] = useState(false);
  const [pulse3dVersions, setPulse3dVersions] = useState([]);
  const [metaPulse3dVersions, setMetaPulse3dVersions] = useState([]);
  const [defaultUploadForReanalysis, setDefaultUploadForReanalysis] = useState();
  const router = useRouter();

  const { accountType, productPage } = useContext(AuthContext);

  const stiffnessFactorDetails = {
    Auto: null,
    "Cardiac (1x)": 1,
    "Skeletal Muscle (12x)": 12,
    // Tanner (11/1/22): if we need to add an option for variable stiffness in the dropdown, a new version of pulse3d will need to be released
  };

  const dataTypeDetails = {
    Auto: null,
    Force: "Force",
    Calcium: "Calcium",
    Voltage: "Voltage",
  };

  // TODO this can probably be refactored be more efficient
  useEffect(() => {
    if (router.pathname === "/uploads" || router.pathname === "/upload-form") {
      if (accountType === "admin") {
        getUploads();
      } else if (accountType === "user" && productPage) {
        getUploads(productPage);
      }
      getPulse3dVersions();
    }
    // reset
    if (fetchUploads) {
      setFetchUploads(false);
    }
  }, [router.pathname, fetchUploads, accountType, productPage]);

  useEffect(() => {
    // clear default upload when user leaves the re-analyze page
    if (router.pathname !== "/upload-form") {
      setDefaultUploadForReanalysis(null);
    }
  }, [router.pathname]);

  const getUploads = async (uploadType) => {
    try {
      let url = `${process.env.NEXT_PUBLIC_PULSE3D_URL}/uploads`;
      if (uploadType) {
        url += `?upload_type=${uploadType}`;
      }
      const response = await fetch(url);

      if (response && response.status === 200) {
        const uploadsArr = await response.json();
        setUploads([...uploadsArr]);
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

      const externalVersions = versions.filter(({ state }) => state === "external");
      const testingVersions = versions.filter(({ state }) => state === "testing");
      const deprecatedVersions = versions.filter(({ state }) => state === "deprecated");

      // sort versions with different state independently so they can still be grouped by state
      const sortedExternalVersions = semverRsort(externalVersions.map(({ version }) => version));
      const sortedTestingVersions = semverRsort(testingVersions.map(({ version }) => version));
      const sortedDeprecatedVersions = semverRsort(deprecatedVersions.map(({ version }) => version));

      setPulse3dVersions([...sortedExternalVersions, ...sortedTestingVersions, ...sortedDeprecatedVersions]);
    } catch (e) {
      console.log(`ERROR getting pulse3d versions: ${e}`);
    }
  }

  return (
    <UploadsContext.Provider
      value={{
        uploads,
        setUploads,
        setFetchUploads,
        pulse3dVersions,
        metaPulse3dVersions,
        stiffnessFactorDetails,
        dataTypeDetails,
        defaultUploadForReanalysis,
        setDefaultUploadForReanalysis,
      }}
    >
      <Container>
        <ControlPanel />
        <PageContainer>{children}</PageContainer>
      </Container>
    </UploadsContext.Provider>
  );
}
