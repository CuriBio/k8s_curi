import { useState } from "react";

export default function useEventSource() {
  const [evtSource, setEvtSource] = useState();

  // TODO delete all the debug logging

  const connect = () => {
    if (evtSource) {
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

      const url = `${process.env.NEXT_PUBLIC_EVENTS_URL}/token`;
      response = await fetch(url, {
        method: "POST",
      });
    });

    // TODO try to reconnect if closed?

    setEvtSource(newEvtSource);
  };

  const disconnect = () => {
    if (!evtSource) {
      console.log("already disconnected");
      return;
    }
    console.log("disconnecting");

    evtSource.close();
    setEvtSource(null);
  };

  return [connect, disconnect];
}
