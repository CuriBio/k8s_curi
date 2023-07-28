import CircularProgressWithLabel from "./CircularProgressWithLabel";
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
  margin-top: 3%;
  display: flex;
  flex-direction: col;
`;

const InnerContainer2 = styled.div`
  width: 33%;
  padding-left: 2%;
  padding-right: 2%;
`;

export default function UsageWidget({
  metricName,
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
    if (isUnlimited) return "Unlimited";
    if (daysOfPlanLeft >= 0) return `${daysOfPlanLeft} days of plan left`;
    return `${daysOfPlanLeft * -1} days expired`;
  })();
  const usageMessage = isUnlimited
    ? `${actualUsage} ${metricName} used`
    : `${actualUsage} out of ${limitUsage} ${metricName} used`;
  const percentUsage = isUnlimited ? 0 : Math.min((actualUsage / limitUsage) * 100, 100);
  const additionalInfo = isUnlimited
    ? "You have unlimited access to Pulse3d analysis."
    : "Each upload comes with one free re-analysis. The initial analysis and all re-analyses after the first one will consume 1 analysis credit each.";

  return (
    <Container>
      <h1>{subscriptionName} Plan</h1>
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
