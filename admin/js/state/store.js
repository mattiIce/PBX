class Store {
  constructor(initialState) {
    this._state = { ...initialState };
    this._listeners = new Map();
  }

  get(key) { return this._state[key]; }

  set(key, value) {
    this._state[key] = value;
    const listeners = this._listeners.get(key) || [];
    listeners.forEach(fn => fn(value));
  }

  subscribe(key, callback) {
    if (!this._listeners.has(key)) this._listeners.set(key, []);
    this._listeners.get(key).push(callback);
    return () => {
      const list = this._listeners.get(key);
      const idx = list.indexOf(callback);
      if (idx > -1) list.splice(idx, 1);
    };
  }

  getState() { return { ...this._state }; }
}

export const store = new Store({
  currentUser: null,
  currentExtensions: [],
  currentTab: 'dashboard',
  isAuthenticated: false,
  autoRefreshInterval: null,
});
