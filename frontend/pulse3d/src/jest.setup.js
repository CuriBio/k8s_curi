import "@testing-library/jest-dom/extend-expect";

class Worker {
  constructor(stringUrl) {
    this.url = stringUrl;
  }

  postMessage(msg) {
    this.onmessage({
      data: { status: 200, type: msg.type, data: [], jobs: [] },
    });
  }

  terminate() {}
}

class URL {
  constructor(stringUrl, base) {
    this.url = stringUrl;
    this.base = base;
  }
}

window.Worker = Worker;
window.URL = URL;

export default {
  Worker,
};
