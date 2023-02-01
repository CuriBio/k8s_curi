import CircularProgressWithLabel from "./CircularProgressWithLabel";
import styled from "styled-components";

const Container = styled.div`
  background: linear-gradient(0, var(--med-gray) 30%, var(--light-gray) 90%);
  box-shadow: 0 3px 5px 2px var(--dark-gray);
  border: 3px solid black;
  padding: 0.75rem;
  border-radius: 3px;
  display: flex;
  align-items: center;
  color: black;
  flex-flow: column;
  text-align: center;
`;
const SmallDescription = styled.div`
  font-size: 0.75rem;
  text-align: center;
`;
export default function UsageWidget({
  metricName,
  limitUsage,
  actualUsage,
  subscriptionName,
  subscriptionEndDate,
  colorOfTextLabel,
  daysOfPlanLeft,
}) {
  return (
    <>
      {parseInt(limitUsage) !== -1 ? (
        <Container>
          <h1>{subscriptionName} Plan</h1>
          <p>{`Plan Expires on ${subscriptionEndDate}`}</p>
          <p>
            {daysOfPlanLeft >= 0
              ? `${daysOfPlanLeft} days of plan left`
              : `${daysOfPlanLeft * -1} days expired`}
          </p>
          <p>{`${actualUsage} out of ${limitUsage} ${metricName} used`}</p>
          <CircularProgressWithLabel
            value={(actualUsage / limitUsage) * 100 > 100 ? 100 : parseInt((actualUsage / limitUsage) * 100)}
            colorOfTextLabel={colorOfTextLabel}
          />
          <SmallDescription>
            Each upload comes with one free re-analysis. Initial analysis and all re-analysis after first one
            will consume an analysis credit.
          </SmallDescription>
        </Container>
      ) : (
        <Container>
          <h1>Unlimited Plan</h1>
          <p>No expiration date</p>
          <p>Unlimited days left</p>
          <p>{`${actualUsage} ${metricName} used`}</p>
          <CircularProgressWithLabel value={0} colorOfTextLabel={colorOfTextLabel} />
          <SmallDescription>You have unlimited access to Pulse3d analysis.</SmallDescription>
        </Container>
      )}
    </>
  );
}
