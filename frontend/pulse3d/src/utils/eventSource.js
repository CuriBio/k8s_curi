import { useState, useEffect } from "react";

export default function useEventSource() {
  const [evtSource, setEvtSource] = useState(null);
  const [desiredConnectionStatus, setDesiredConnectionStatus] = useState(false);
  const [updates, setUpdates] = useState([]);

  useEffect(() => {
    if (desiredConnectionStatus) {
      connect();
    } else {
      disconnect();
    }
  }, [desiredConnectionStatus]);

  const connect = () => {
    if (evtSource != null) {
      return;
    }

    createEvtSource();
  };

  const disconnect = () => {
    if (evtSource == null) {
      return;
    }

    evtSource.close();
    setEvtSource(null);
  };

  const createEvtSource = () => {
    const newEvtSource = new EventSource(`${process.env.NEXT_PUBLIC_EVENTS_URL}/stream`);

    newEvtSource.addEventListener("error", (e) => {
      newEvtSource.close();
      setTimeout(() => {
        if (desiredConnectionStatus) {
          createEvtSource();
        }
      }, 5000);
    });

    newEvtSource.addEventListener("data_update", (e) => {
      const payload = JSON.parse(e.data);

      setUpdates([{ event: "data_update", payload }, ...updates]);
    });

    newEvtSource.addEventListener("usage_update", function (e) {
      const payload = JSON.parse(e.data);

      setUpdates([{ event: "usage_update", payload }, ...updates]);
    });

    newEvtSource.addEventListener("token_expired", async function (e) {
      await fetch(`${process.env.NEXT_PUBLIC_EVENTS_URL}/token`, {
        method: "POST",
      });
    });

    setEvtSource(newEvtSource);
  };
  return { setDesiredConnectionStatus, updates };
}
