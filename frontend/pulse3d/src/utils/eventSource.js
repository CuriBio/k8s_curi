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

    const newEvtSource = new EventSource(`${process.env.NEXT_PUBLIC_EVENTS_URL}/stream`);

    newEvtSource.addEventListener("data_update", function (event) {
      console.log("data_update", event.data);

      // TODO handle the update
    });

    newEvtSource.addEventListener("usage_update", function (event) {
      console.log("usage_update", event.data);

      // TODO handle the update
    });

    newEvtSource.addEventListener("token_expired", async function (event) {
      console.log("token_expired");

      await fetch(`${process.env.NEXT_PUBLIC_EVENTS_URL}/token`, {
        method: "POST",
      });
    });

    // TODO try to detect a disconnect and then reconnect

    setEvtSource(newEvtSource);
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

  return setDesiredConnectionStatus;
}
