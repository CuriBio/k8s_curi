import CircularProgressWithLabel from "./CircularProgressWithLabel";
export default function UsageWidget({
  metricName,
  limitUsage,
  actualUsage,
  subscriptionName,
  subscriptionEndDate,
  labeltextcolor,
  daysOfPlanLeft,
}) {
  return (
    <>
      <div id="container">
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
          labeltextcolor={labeltextcolor}
        />
        <p id="smallDescription">
          Each upload comes with one free initial analysis and one free re-analysis. All subsequent analyses
          of an uploaded file will use a credit.
        </p>
      </div>
      <style jsx>{`
        div#container {
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
        }
        p#smallDescription {
          font-size: 0.75rem;
          text-align: center;
        }
      `}</style>
    </>
  );
}
