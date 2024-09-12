import CircularProgressWithLabel from "@/components/basicWidgets/CircularProgressWithLabel";
import styled from "styled-components";

const Container = styled.div`
  display: flex;
  align-items: center;
  flex-flow: column;
  text-align: center;
`;

const SmallDescription = styled.div`
  font-size: 0.75rem;
  text-align: center;
  white-space: pre-wrap;
  overflow-wrap: break-word;
`;

const InnerContainer1 = styled.div`
  margin-top: 2%;
  display: flex;
  flex-direction: col;
`;

const InnerContainer2 = styled.div`
  width: 33%;
  padding-left: 2%;
  padding-right: 2%;
`;

const Header = styled.h1`
  font-size: 25px;
`;

const getAdditionalInfoMsg = (productPage, isUnlimited, limitUsage) => {
  if (isUnlimited) {
    let productDisplay = productPage;
    if (productDisplay === "advanced_analysis") {
      productDisplay = "Advanced";
    }
    return `You have unlimited ${productDisplay} Analyses.`;
  } else {
    if (["mantarray", "nautilai"].includes(productPage)) {
      return "Each upload comes with one free re-analysis. The initial analysis and all re-analyses after the first one will consume 1 analysis credit each.";
    } else if (productPage === "advanced_analysis") {
      const vowel = limitUsage === 1 ? "i" : "e";
      return `You have ${limitUsage} total Advanced Analys${vowel}s.`;
    }
  }
};

export default function UsageWidget({
  metricName,
  productPage,
  limitUsage,
  actualUsage,
  subscriptionEndDate,
  colorOfTextLabel,
  daysOfPlanLeft,
}) {
  const isUnlimited = limitUsage === -1;

  const subscriptionName = isUnlimited ? "Unlimited" : "Basic";
  const expirationMessage = subscriptionEndDate
    ? `Plan Expires on ${subscriptionEndDate}`
    : "No Expiration Date";
  const remainingTimeMessage = (() => {
    if (!subscriptionEndDate) {
      return "Unlimited";
    } else if (daysOfPlanLeft >= 0) {
      return `${daysOfPlanLeft} days of plan left`;
    } else {
      return `${daysOfPlanLeft * -1} days expired`;
    }
  })();

  const usageMessage = isUnlimited
    ? `${actualUsage} ${metricName} used`
    : `${actualUsage} out of ${limitUsage} ${metricName} used`;

  const percentUsage = isUnlimited ? 0 : Math.min((actualUsage / limitUsage) * 100, 100);
  const additionalInfo = getAdditionalInfoMsg(productPage, isUnlimited, limitUsage);

  return (
    <Container>
      <Header>{subscriptionName} Plan</Header>
      <InnerContainer1>
        <InnerContainer2>
          <p>{expirationMessage}</p>
          <p>{remainingTimeMessage}</p>
        </InnerContainer2>
        <InnerContainer2>
          <CircularProgressWithLabel
            value={percentUsage}
            size={130}
            fontSize={25}
            colorOfTextLabel={colorOfTextLabel}
          />
        </InnerContainer2>
        <InnerContainer2>
          <p>{usageMessage}</p>
          <SmallDescription>{additionalInfo}</SmallDescription>
        </InnerContainer2>
      </InnerContainer1>
    </Container>
  );
}
