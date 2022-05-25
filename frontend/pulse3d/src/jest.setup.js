import '@testing-library/jest-dom/extend-expect';

class Worker {
  constructor(stringUrl) {
    this.url = stringUrl;
    this.onmessage = () => {};
  }

  postMessage(msg) {
    this.onmessage(msg);
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
