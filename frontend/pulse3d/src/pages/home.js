import styled from "styled-components";
import { useState, useContext, useEffect } from "react";
import { useRouter } from "next/router";
import Image from "next/image";
import { AuthContext } from "@/pages/_app";

// required for static export, default loader errors on build
const imageLoader = ({ src }) => {
  return src;
};
const BackgroundContainer = styled.div`
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 65px;
  width: 100%;
  height: 95vh;
  flex-direction: column;
  background: var(--dark-gray);
  overflow-x: scroll;
`;

const RowContainer = styled.div`
  position: relative;
  min-width: 1400px;
  min-height: 35%;
  display: flex;
  justify-content: center;
`;

const ImageLabelContainer = styled.div`
  display: flex;
  flex-direction: Column;
  position: relative;
  justify-content: center;
  align-items: center;
  margin: 0 100px;
`;

const ProductLabel = styled.div`
  font-size: 16px;
  font-weight: bolder;
  margin: 7px;
  cursor: default;
`;

const ProductDescLabel = styled.div`
  font-size: 10px;
  cursor: default;
`;

export default function Login() {
  const router = useRouter();
  const { accountScope, setProductPage, setUsageQuota, setPreferences } = useContext(AuthContext);

  const [products, setProducts] = useState({
    mantarray: {
      name: "Mantarray",
      description: "3D Tissue Contractility Analysis",
      state: "disabled",
    },
    nautilus: {
      name: "Nautilus",
      description: "2D & 3D Calcium & Voltage Analysis",
      state: "disabled",
    },
    pulse2d: {
      name: "Pulse2D",
      description: "2D Cell Contractility Analysis",
      state: "disabled",
    },
    phenolearn: {
      name: "PhenoLearn",
      description: "AI/ML Platform",
      state: "disabled",
    },
    "analysis tools": {
      name: "Advanced Analysis Tools",
      description: "",
      state: "disabled",
    },
  });

  useEffect(() => {
    // TODO come up with a better way to match account scopes and all products
    if (accountScope) {
      const productStates = JSON.parse(JSON.stringify(products));

      for (const product of Object.keys(products)) {
        const isProductAvailable = accountScope.some((scope) => scope.includes(product));

        productStates[product].state = isProductAvailable ? "default" : "disabled";
      }

      setProducts(productStates);
      getPreferences();
    }
  }, [accountScope]);

  useEffect(() => {
    // reset usage quota each time the home page is navigated too so that the previous product usage doesn't affect navigating to a different product
    setUsageQuota();
  }, []);

  const getPreferences = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_USERS_URL}/preferences`);
      res && setPreferences(await res.json());
    } catch (e) {
      console.log("ERROR getting user preferences");
    }
  };

  const mouseEnter = ({ target }) => {
    const productType = target.id.split("-")[0];
    // protect against hovering over disabled products
    if (products[productType].state === "default") {
      setProducts({ ...products, [productType]: { ...products[productType], state: "hover" } });
    }
  };

  const mouseLeave = ({ target }) => {
    const productType = target.id.split("-")[0];
    // protect against non hovered products
    if (products[productType].state === "hover") {
      setProducts({ ...products, [productType]: { ...products[productType], state: "default" } });
    }
  };

  const handleProductNavigation = ({ target }) => {
    if (!target.id.includes("disabled")) {
      // used to poll usage for correct product
      setProductPage(target.id.split("-")[0]);
      // TODO handle different nav once product differences are more specced out
      router.push("/uploads?checkUsage=true", "/uploads");
    }
  };

  return (
    <BackgroundContainer>
      {[
        ["mantarray", "nautilus"],
        ["pulse2d", "phenolearn", "analysis tools"],
      ].map((row, idx) => {
        return (
          <RowContainer key={idx}>
            {row.map((type) => {
              const { name, description, state } = products[type];

              // enabled
              let color = "#ececed";
              let cursor = "pointer";
              // else
              if (state === "disabled") {
                color = "#4c4c4c";
                cursor = "default";
              } else if (state === "hover") {
                color = "#ffffff";
              }

              return (
                <ImageLabelContainer key={type} style={{ color }}>
                  <Image
                    src={`/Curi-Bio-cloud-design_${type} ${state} state.svg`}
                    alt={`${name} logo`}
                    id={`${type}-${state}`}
                    width={250}
                    height={250}
                    loader={imageLoader}
                    style={{ cursor }}
                    unoptimized
                    onMouseEnter={mouseEnter}
                    onMouseLeave={mouseLeave}
                    onClick={handleProductNavigation}
                    priority={state === "hover"} // increases loading speed from lazy
                  />
                  <ProductLabel>{name}</ProductLabel>
                  <ProductDescLabel>{description}</ProductDescLabel>
                </ImageLabelContainer>
              );
            })}
          </RowContainer>
        );
      })}
    </BackgroundContainer>
  );
}
