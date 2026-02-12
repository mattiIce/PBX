/**
 * Callback type for state change listeners.
 * Receives the new value for the subscribed key.
 */
export type Listener<T> = (value: T) => void;

/**
 * A simple reactive key-value store with per-key subscriptions.
 *
 * @typeParam T - The shape of the state object, constrained to a
 *   record of string keys with unknown values.
 */
class Store<T extends Record<string, unknown>> {
    private _state: T;
    private _listeners: Map<keyof T, Listener<T[keyof T]>[]>;

    constructor(initialState: T) {
        this._state = { ...initialState };
        this._listeners = new Map();
    }

    get<K extends keyof T>(key: K): T[K] {
        return this._state[key];
    }

    set<K extends keyof T>(key: K, value: T[K]): void {
        this._state[key] = value;
        const listeners = this._listeners.get(key) || [];
        listeners.forEach((fn) => fn(value));
    }

    /**
     * Subscribe to changes for a specific key in the store.
     * Returns an unsubscribe function.
     */
    subscribe<K extends keyof T>(key: K, callback: Listener<T[K]>): () => void {
        if (!this._listeners.has(key)) {
            this._listeners.set(key, []);
        }
        // We know the array exists because we just ensured it above
        const list = this._listeners.get(key)!;
        list.push(callback as Listener<T[keyof T]>);

        return () => {
            const currentList = this._listeners.get(key);
            if (!currentList) return;
            const idx = currentList.indexOf(callback as Listener<T[keyof T]>);
            if (idx > -1) currentList.splice(idx, 1);
        };
    }

    getState(): T {
        return { ...this._state };
    }
}

/**
 * Shape of the global PBX admin state.
 */
export interface PbxState {
    currentUser: string | null;
    currentExtensions: unknown[];
    currentTab: string;
    isAuthenticated: boolean;
    autoRefreshInterval: number | null;
}

export const store = new Store<PbxState>({
    currentUser: null,
    currentExtensions: [],
    currentTab: 'dashboard',
    isAuthenticated: false,
    autoRefreshInterval: null,
});
