import { useState, useEffect } from "react";

export default function useEventSource() {
  const [evtSource, setEvtSource] = useState(null);
  const [desiredConnectionStatus, setDesiredConnectionStatus] = useState(false);

  useEffect(() => {
    if (desiredConnectionStatus) {
      connect();
    } else {
      disconnect();
    }
  }, [desiredConnectionStatus]);

  // TODO delete all the debug logging

  const connect = () => {
    console.log("connect:", evtSource);
    if (evtSource != null) {
      console.log("already connected");
      return;
    }
    console.log("connecting");

    createEvtSource();
  };

  const disconnect = () => {
    console.log("disconnect:", evtSource);
    if (evtSource == null) {
      console.log("already disconnected");
      return;
    }
    console.log("disconnecting");

    evtSource.close();
    setEvtSource(null);
  };

  const createEvtSource = () => {
    const newEvtSource = new EventSource(`${process.env.NEXT_PUBLIC_EVENTS_URL}/stream`);

    newEvtSource.addEventListener("open", (e) => {
      console.log("OPEN");
    });

    newEvtSource.addEventListener("error", (e) => {
      console.log("ERROR", e);
      console.log("READY STATE", newEvtSource.readyState);
      newEvtSource.close();
      setTimeout(() => {
        if (desiredConnectionStatus) {
          createEvtSource();
        }
      }, 5000);
    });

    newEvtSource.addEventListener("data_update", (e) => {
      console.log("data_update", e.data);

      // TODO handle the update
    });

    newEvtSource.addEventListener("usage_update", function (e) {
      console.log("usage_update", e.data);

      // TODO handle the update
    });

    newEvtSource.addEventListener("token_expired", async function (e) {
      console.log("token_expired");

      await fetch(`${process.env.NEXT_PUBLIC_EVENTS_URL}/token`, {
        method: "POST",
      });
    });

    setEvtSource(newEvtSource);
  };
  return setDesiredConnectionStatus;
}
