import DashboardLayout from "@/components/layouts/DashboardLayout";
import styled from "styled-components";
import Image from "next/image";
// required for static export, default loader errors on build
const imageLoader = ({ src }) => {
  return src;
};

const BackgroundContainer = styled.div`
  width: 90%;
  margin: 5%;
  align-items: left;
  display: flex;
  justify-content: center;
`;

export default function Metrics() {
  return (
    <BackgroundContainer>
      <Image
        src={"/twitch_metrics_diagram.png"}
        alt="Twitch Metrics Diagram"
        width={800}
        height={1000}
        loader={imageLoader}
        unoptimized
      />
    </BackgroundContainer>
  );
}

Metrics.getLayout = (page) => {
  return <DashboardLayout>{page}</DashboardLayout>;
};
