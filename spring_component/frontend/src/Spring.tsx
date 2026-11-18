import { useEffect, useRef, useState } from 'react';
import { HeroScene, type Interactive } from './lab/engine/scene';
import { canRunLive3d, canUseWebGL, forceLive3d } from './webgl';
import { Streamlit, type SpringArgs } from './streamlit';

/** The four things in the spring that respond to a tap: today's quest in Atlas. */
const FINDABLE: Interactive[] = ['ripple', 'water', 'pad', 'spout'];

/**
 * Ripple's spring inside the Streamlit app. Python owns the numbers (total, goal, each drink);
 * this component only shows them: the water level follows the day's progress, each new drink
 * pours from the bamboo spout, and Ripple reacts. Taps found in the scene are sent back to
 * Python for the Atlas quest. Nothing here ever logs water.
 */
export function Spring() {
  const [args, setArgs] = useState<SpringArgs | null>(null);
  const [live, setLive] = useState(() => canRunLive3d());
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<HeroScene | null>(null);
  const lastPour = useRef<number | null>(null);
  const found = useRef(new Set<string>());

  // Listen for Python's arguments, then tell Streamlit the component is ready.
  useEffect(() => {
    const off = Streamlit.onRender(setArgs);
    Streamlit.ready();
    return off;
  }, []);

  const full = args?.height === 0;
  useEffect(() => {
    if (args) Streamlit.setFrameHeight(full ? 1 : args.height);
  }, [args?.height]); // eslint-disable-line react-hooks/exhaustive-deps

  const progress = args ? Math.min(1, args.total_ml / Math.max(1, args.goal_ml)) : 0;
  const haveArgs = args !== null;

  // Build the scene once Python's first arguments have arrived.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!haveArgs || !live || failed || !canvas || !args) return;
    let scene: HeroScene;
    try {
      scene = new HeroScene(canvas, {
        reduced: args.reduced,
        buddy: 'sprite',
        progress,
        explore: args.explore,
        callbacks: {
          onDisplayMl: () => {},
          onPourDone: () => {},
          onQuality: () => {},
          onReaction: () => {},
          onContextLost: () => setFailed(true),
          onBuddyState: (st) => {
            if (st !== 'loading') setReady(true);
          },
          onInteract: (what) => {
            if (!FINDABLE.includes(what) || found.current.has(what)) return;
            found.current.add(what);
            Streamlit.setComponentValue({ found: [...found.current] });
          }
        }
      });
    } catch {
      setFailed(true);
      return;
    }
    scene.setSound(args.sound);
    sceneRef.current = scene;
    applyFraming(scene, args);
    // A drink logged before this view opened has already poured: don't replay it.
    lastPour.current = args.pour?.id ?? null;
    return () => {
      scene.dispose();
      sceneRef.current = null;
    };
    // The scene is made once; later changes are pushed by the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [haveArgs, live, failed]);

  // Every rerun: pour a new drink, or let the water settle to the true level (a reset or an edit).
  useEffect(() => {
    const s = sceneRef.current;
    if (!s || !args) return;
    s.setReduced(args.reduced);
    s.setSound(args.sound);
    applyFraming(s, args);
    const p = args.pour;
    if (p && p.id !== lastPour.current) {
      lastPour.current = p.id;
      const ok = s.logGlass({
        fromMl: p.from_ml,
        toMl: p.to_ml,
        goal: args.goal_ml,
        reachedGoal: p.reached_goal,
        pastGoal: p.past_goal
      });
      if (!ok) s.setProgress(progress, true);
    } else if (!s.pouring) {
      s.setProgress(progress, true);
    }
  }, [args, progress]);

  // Phone and desktop frame Ripple differently: follow the window when it is resized or rotated.
  useEffect(() => {
    const onResize = () => {
      if (sceneRef.current && args) applyFraming(sceneRef.current, args);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [args]);

  if (!args) return null;
  const showLive = live && !failed;
  return (
    <div
      className={full ? 'spring full' : 'spring'}
      style={{ height: full ? '100vh' : args.height }}
      data-ready={(showLive && ready) || undefined}
    >
      <img className="poster" src="./ripple-poster.webp" alt="" aria-hidden="true" />
      {showLive && <canvas ref={canvasRef} className="canvas" aria-hidden="true" />}
      {showLive && !ready && (
        <p className="badge" role="status">
          Ripple is on the way…
        </p>
      )}
      {!showLive && canUseWebGL() && !failed && (
        <div className="badge note">
          <span>This device draws 3D without a graphics chip, so the spring stays still.</span>
          <button
            type="button"
            onClick={() => {
              forceLive3d();
              setLive(true);
            }}
          >
            Show it anyway
          </button>
        </div>
      )}
      {(failed || !canUseWebGL()) && <p className="badge">The spring is shown as a still picture on this device.</p>}
    </div>
  );
}

/** Where Ripple sits in the view. In Atlas this only sets where the free camera looks. */
function applyFraming(scene: HeroScene, args: SpringArgs) {
  const narrow = window.innerWidth < 700;
  if (args.explore) {
    if (args.framing_explore && !narrow) scene.setFraming(...args.framing_explore);
    return;
  }
  const f = (narrow ? args.framing_narrow : args.framing) ?? args.framing ?? [-0.6, 0.42, 0.45];
  scene.setFraming(f[0], f[1], f[2]);
}
