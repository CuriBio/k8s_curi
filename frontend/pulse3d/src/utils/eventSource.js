import { useState, useEffect, useRef } from "react";
import { formatJob } from "@/utils/generic";

const getPayload = (e, listenerName) => {
  try {
    const payload = JSON.parse(e.data);
    return payload;
  } catch (err) {
    console.error(`ERROR parsing data of ${listenerName} event`, err);
  }
};

export default function useEventSource(hooks) {
  const [evtSource, setEvtSource] = useState(null);
  const [desiredConnectionStatus, setDesiredConnectionStatus] = useState(false);

  const hooksRef = useRef({ ...hooks, desiredConnectionStatus });

  useEffect(() => {
    if (desiredConnectionStatus) {
      connect();
    } else {
      disconnect();
    }
  }, [desiredConnectionStatus]);

  useEffect(() => {
    hooksRef.current = { ...hooks, desiredConnectionStatus };
  }, [hooks, desiredConnectionStatus]);

  const connect = () => {
    if (evtSource != null) {
      return;
    }

    createEvtSource(5000);
  };

  const disconnect = () => {
    if (evtSource == null) {
      return;
    }

    evtSource.close();
    setEvtSource(null);
  };

  const createEvtSource = (timeout) => {
    const newEvtSource = new EventSource(`${process.env.NEXT_PUBLIC_EVENTS_URL}/stream`);

    newEvtSource.addEventListener("error", (e) => {
      newEvtSource.close();

      setTimeout(() => {
        if (hooksRef.current.desiredConnectionStatus) {
          const newTimeout = Math.min(timeout * 2, 60e3);
          createEvtSource(newTimeout);
        }
      }, timeout);
    });

    newEvtSource.addEventListener("data_update", (e) => {
      const payload = getPayload(e, "data_update");

      if (
        (hooksRef.current.accountType !== "admin" && payload["product"] !== hooksRef.current.productPage) ||
        hooksRef.current.jobs.length === 0
      ) {
        return;
      }

      if (payload.usage_type === "uploads") {
        const { uploads, setUploads } = hooksRef.current;

        // currently there is nothing to update if the upload is already present, so only add new uploads
        if (!uploads.some((upload) => upload.id == payload.id)) {
          setUploads([payload, ...uploads]);
        }
      } else if (payload.usage_type === "jobs") {
        const { jobs, setJobs } = hooksRef.current;

        for (const [i, job] of jobs.entries()) {
          if (job.jobId === payload.id) {
            jobs[i] = formatJob(payload, {}, hooksRef.current.accountId);
            jobs[i].checked = job.checked;
            setJobs([...jobs]);
            return;
          }
        }

        setJobs([formatJob(payload, {}, hooksRef.current.accountId), ...jobs]);
      }
    });

    newEvtSource.addEventListener("usage_update", function (e) {
      const payload = getPayload(e, "usage_update");

      if (hooksRef.current.accountType !== "admin" && payload["product"] !== hooksRef.current.productPage) {
        return;
      }

      const { usageQuota, setUsageQuota } = hooksRef.current;

      if (Object.keys(usageQuota || {}).length > 0) {
        usageQuota.current[payload.usage_type] = payload.usage;
        setUsageQuota({ ...usageQuota });
      }
    });

    newEvtSource.addEventListener("token_expired", async function (e) {
      await fetch(`${process.env.NEXT_PUBLIC_EVENTS_URL}/token`, {
        method: "POST",
      });
    });

    setEvtSource(newEvtSource);
  };
  return { setDesiredConnectionStatus };
}
