import ControlPanel from "@/components/layouts/ControlPanel";
import { useEffect, useContext } from "react";
import styled from "styled-components";
import { useRouter } from "next/router";
import semverRsort from "semver/functions/rsort";
import { AuthContext, UploadsContext, AdvancedAnalysisContext } from "@/pages/_app";

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

export default function DashboardLayout({ children }) {
  const router = useRouter();

  const { accountType, productPage } = useContext(AuthContext);

  const {
    uploads,
    getUploadsAndJobs,
    setPulse3dVersions,
    setMetaPulse3dVersions,
    setDefaultUploadForReanalysis,
  } = useContext(UploadsContext);

  const { advancedAnalysisJobs, getAdvancedAnalysisJobs } = useContext(AdvancedAnalysisContext);

  const getUploadsAndJobsIfEmpty = (productPage) => {
    if (uploads?.length === 0) {
      getUploadsAndJobs(productPage);
    }
  };

  const getAdvancedAnalysisJobsIfEmpty = () => {
    if (advancedAnalysisJobs.length === 0) {
      getAdvancedAnalysisJobs();
    }
  };

  useEffect(() => {
    if (accountType === "admin") {
      getUploadsAndJobsIfEmpty();
    } else if (accountType === "user") {
      if (["mantarray", "nautilai"].includes(productPage)) {
        getUploadsAndJobsIfEmpty(productPage);
      } else if (productPage === "advanced_analysis") {
        getAdvancedAnalysisJobsIfEmpty();
      }
    }
  }, [productPage, accountType]);

  useEffect(() => {
    getPulse3dVersions();
  }, []);

  useEffect(() => {
    // clear default upload when user leaves the re-analyze page
    if (router.pathname !== "/upload-form") {
      setDefaultUploadForReanalysis(null);
    }
  }, [router.pathname]);

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
    <Container>
      <ControlPanel />
      <PageContainer>{children}</PageContainer>
    </Container>
  );
}
