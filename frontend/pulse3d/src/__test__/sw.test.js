let listeners = {};

self.addEventListener = (eventName, fn) => {
  listeners[eventName] = fn;
};

// self.trigger = (eventName) => {
//     listeners[eventName]()
// }

describe("Service worker", () => {
  beforeEach(() => {
    listeners = {};
    jest.resetModules();
  });

  describe("initialization", () => {
    let serviceWorkerInternals;
    beforeEach(() => {
      serviceWorkerInternals = require("../serviceWorker.js").accessToInternalsForTesting;
    });

    it("should add listeners", () => {
      expect(listeners.install).toBeDefined();
      expect(listeners.activate).toBeDefined();
      expect(listeners.fetch).toBeDefined();
      expect(self.onmessage).toBeDefined();
    });

    it("should set global vars to null", () => {
      expect(serviceWorkerInternals.accountType).toBeNull();
      expect(serviceWorkerInternals.tokens.access).toBeNull();
      expect(serviceWorkerInternals.tokens.refresh).toBeNull();
      expect(serviceWorkerInternals.logoutTimer).toBeNull();
      expect(serviceWorkerInternals.ClientSource).toBeNull();
    });
  });
});
