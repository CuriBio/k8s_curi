import { useContext, useState, useEffect } from "react";
import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import Image from "next/image";
import { useRouter } from "next/router";

// required for static export, default loader errors on build
const imageLoader = ({ src }) => {
  return src;
};

import { AuthContext } from "@/pages/_app";

const BackgroundContainer = styled.div`
  width: 90%;
  margin: 5%;
  align-items: left;
  display: flex;
  justify-content: center;
`;

const getImages = (productPage, metricsVersion) => {
  const version = metricsVersion || 1;

  if (productPage === "mantarray") {
    return (
      <Image
        src={`/mantarray_twitch_metrics_diagram_v${version}.png`}
        alt="Mantarray Twitch Metrics Diagram"
        width={800}
        height={1000}
        loader={imageLoader}
        unoptimized
      />
    );
  } else if (productPage === "nautilai") {
    return (
      <>
        <Image
          src={`/nautilai_twitch_metrics_diagram_v${version}.png`}
          alt="Nautilai Twitch Metrics Diagram"
          width={800}
          height={1000}
          loader={imageLoader}
          unoptimized
        />
        <Image
          src={"/nautilai_detrending_and_normalization.png"}
          alt="Nautilai Detrending and Normalization Diagram"
          width={800}
          height={1000}
          loader={imageLoader}
          unoptimized
        />
      </>
    );
  } else {
    return <></>;
  }
};

export default function Metrics() {
  const router = useRouter();
  const { productPage } = useContext(AuthContext);
  const [metricsVersion, setMetricsVersion] = useState(null);

  useEffect(() => {
    setMetricsVersion(router?.query?.id?.toLowerCase() === "v2" ? 2 : 1);
  }, [router.query]);

  return <BackgroundContainer>{getImages(productPage, metricsVersion)}</BackgroundContainer>;
}

Metrics.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
