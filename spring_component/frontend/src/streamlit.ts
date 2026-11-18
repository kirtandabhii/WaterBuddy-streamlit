/**
 * The few messages a Streamlit component exchanges with the Streamlit app around it
 * (the same protocol `streamlit-component-lib` uses, written out so nothing else is needed).
 * Python's arguments arrive in "streamlit:render"; values go back with setComponentValue,
 * which reruns the Python script with the new value.
 */
export interface SpringArgs {
  total_ml: number;
  goal_ml: number;
  /** True on Atlas: the camera can be turned and zoomed. False on Today: taps only. */
  explore: boolean;
  /** Pixels; 0 fills the whole window (the app shows the spring behind everything). */
  height: number;
  /** Camera offset [x, y, distance] when not exploring; `framing_narrow` on phone-width screens. */
  framing?: [number, number, number] | null;
  framing_narrow?: [number, number, number] | null;
  /** Starting offset in Atlas (the camera stays free to turn and zoom around it). */
  framing_explore?: [number, number, number] | null;
  /** The drink just logged in Python, so the spout pours it. `id` changes with every new drink. */
  pour: { id: number; from_ml: number; to_ml: number; reached_goal: boolean; past_goal: boolean } | null;
  reduced: boolean;
  sound: boolean;
}

function send(type: string, data: Record<string, unknown> = {}) {
  window.parent.postMessage({ isStreamlitMessage: true, type, ...data }, '*');
}

export const Streamlit = {
  ready() {
    send('streamlit:componentReady', { apiVersion: 1 });
  },
  setFrameHeight(height: number) {
    send('streamlit:setFrameHeight', { height });
  },
  setComponentValue(value: unknown) {
    send('streamlit:setComponentValue', { value, dataType: 'json' });
  },
  /** Calls `fn` with Python's arguments on every rerun. Returns an unsubscribe function. */
  onRender(fn: (args: SpringArgs) => void) {
    const handler = (e: MessageEvent) => {
      const d = e.data as { type?: string; args?: SpringArgs } | null;
      if (d && d.type === 'streamlit:render' && d.args) fn(d.args);
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }
};
