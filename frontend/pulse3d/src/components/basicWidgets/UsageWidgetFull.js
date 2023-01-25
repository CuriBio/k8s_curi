import CircularProgressWithLabel from "./CircularProgressWithLabel";
export default function UsageWidget({
  metricName,
  limitUsage,
  actualUsage,
  subscriptionName,
  subscriptionEndDate,
  labelColor,
}) {
  return (
    <>
      <div id="container">
        <h1>{metricName} Usage</h1>
        <p>{subscriptionName} Plan</p>
        <p>Plan Expires on {subscriptionEndDate}</p>
        <p>{`${actualUsage} out of ${limitUsage} ${metricName} used`}</p>
        <CircularProgressWithLabel
          value={(actualUsage / limitUsage) * 100 > 100 ? 100 : parseInt((actualUsage / limitUsage) * 100)}
          labelColor={labelColor}
        />
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
        }
      `}</style>
    </>
  );
}
