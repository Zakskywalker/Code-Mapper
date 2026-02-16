class EventBus {
  constructor() {
    this.handlers = new Map();
  }

  on(event, handler) {
    if (!this.handlers.has(event)) this.handlers.set(event, []);
    this.handlers.get(event).push(handler);
  }

  emit(event, payload) {
    const list = this.handlers.get(event) || [];
    for (const handler of list) handler(payload);
  }
}

const bus = new EventBus();
window.bus = bus;
