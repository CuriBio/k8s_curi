import { useState, useEffect, useRef } from "react";
import { formatAdvancedAnalysisJob, formatP3dJob } from "@/utils/generic";

const getPayload = (e, listenerName) => {
  try {
    const payload = JSON.parse(e.data);
    return payload;
  } catch (err) {
    console.error(`ERROR parsing data of ${listenerName} event`, err);
    return null;
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
      if (payload == null) {
        return;
      }
      // TODO race conditions can be caused by multiple updates happening at once, could probably fix this by
      // acquiring a mutex prior to accessing hooksRef

      // TODO try to remove all this conditional logic here. Probably better to check usage_type and then decide what to do
      if (hooksRef.current.accountType === "admin") {
        if (payload.product === "advanced_analysis") {
          return; // TODO
        }
        if (hooksRef.current.jobs.length === 0) {
          return;
        }
      } else {
        if (payload.product !== hooksRef.current.productPage) {
          // user account must have a product page set
          return;
        } else if (["mantarray", "nautilai"].includes(payload.product)) {
          if (hooksRef.current.jobs.length === 0) {
            return;
          }
        }
      }

      if (payload.usage_type === "uploads") {
        const { uploads, setUploads } = hooksRef.current;
        if (uploads == null) {
          return;
        }

        // currently there is nothing to update if the upload is already present, so only add new uploads or delete existing uploads
        let uploadIdx = -1;
        uploads.map((upload, idx) => {
          if (upload.id === payload.id && uploadIdx === -1) {
            uploadIdx = idx;
          }
        });
        const isUploadPresent = uploadIdx !== -1;
        if (isUploadPresent && payload.deleted) {
          uploads.splice(uploadIdx, 1);
          setUploads([...uploads]);
        } else if (!isUploadPresent && !payload.deleted) {
          setUploads([payload, ...uploads]);
        }
      } else if (payload.usage_type === "jobs") {
        const { jobs, setJobs } = hooksRef.current;

        const formattedJob = formatP3dJob(payload, {}, hooksRef.current.accountId);
        if (formattedJob === null) {
          return;
        }
        // if job is present, update it in place then return
        for (const [i, job] of jobs.entries()) {
          if (job.jobId === payload.id) {
            if (formattedJob.status === "deleted") {
              jobs.splice(i, 1);
            } else {
              jobs[i] = formattedJob;
            }
            setJobs([...jobs]);
            return;
          }
        }
        // job is not present, so just add it
        if (formattedJob.status !== "deleted") {
          setJobs([formattedJob, ...jobs]);
        }
      } else if (payload.usage_type === "advanced_analysis") {
        const { advancedAnalysisJobs, setAdvancedAnalysisJobs } = hooksRef.current;
        if (advancedAnalysisJobs == null) {
          return;
        }

        const formattedJob = formatAdvancedAnalysisJob(payload);
        if (formattedJob === null) {
          return;
        }
        // if job is present, update it in place then return
        for (const [i, job] of advancedAnalysisJobs.entries()) {
          if (job.id === payload.id) {
            if (formattedJob.status === "deleted") {
              advancedAnalysisJobs.splice(i, 1);
            } else {
              advancedAnalysisJobs[i] = formattedJob;
            }
            setAdvancedAnalysisJobs([...advancedAnalysisJobs]);
            return;
          }
        }
        // job is not present, so just add it
        if (formattedJob.status !== "deleted") {
          setAdvancedAnalysisJobs([formattedJob, ...advancedAnalysisJobs]);
        }
      }
    });

    newEvtSource.addEventListener("usage_update", function (e) {
      const payload = getPayload(e, "usage_update");
      if (payload.product !== hooksRef.current.productPage) {
        return;
      }

      const { usageQuota, setUsageQuota } = hooksRef.current;

      let key = payload.usage_type;
      if (payload.product === "advanced_analysis") {
        key = "jobs";
      }

      if (Object.keys(usageQuota || {}).length > 0) {
        usageQuota.current[key] = payload.usage;
        setUsageQuota({ ...usageQuota });
      }
    });

    newEvtSource.addEventListener("notifications_update", function (e) {
      hooksRef.current.getNotificationMessages(e.data.id);
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
