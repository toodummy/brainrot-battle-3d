// Brainrot Battle 3D renderer: Three.js fighters + stage under the existing 2D effects/HUD canvas.
import * as THREE from 'three';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { DRACOLoader } from './vendor/DRACOLoader.js';
import { OutlineEffect } from './vendor/OutlineEffect.js';
import * as SkeletonUtils from './vendor/SkeletonUtils.js';

const MODELS = { shark: 'models/shark.glb', boss: 'models/boss.glb' };
const HEIGHT_K = { shark: 1.0, boss: 1.0 };   // model bbox height -> F.h * k
const D = 2400;                // camera distance to fight plane (world units = 2D px units)
const ELEV = Math.tan(9 * Math.PI / 180);   // camera elevation angle

let renderer, scene, camera, effect, cv3, sun, ready = false, lastGT = -1, lastReal = 0;
const GLTF = {}, LOADING = {};
const INST = new Map();      // fighter object -> instance
const OVR = new Map();       // fighter -> 2D finisher override this frame
let gradTex;

function toonGradient() {
  const d = new Uint8Array([70, 70, 70, 255, 160, 160, 160, 255, 255, 255, 255, 255]);
  const t = new THREE.DataTexture(d, 3, 1, THREE.RGBAFormat); t.minFilter = t.magFilter = THREE.NearestFilter; t.needsUpdate = true; return t;
}

function rimify(m, rim, k) {
  m.onBeforeCompile = (sh) => {
    sh.uniforms.rimColor = { value: new THREE.Color(rim) }; sh.uniforms.rimK = { value: k };
    sh.uniforms.flashC = m.userData.flashU;
    sh.fragmentShader = 'uniform vec3 rimColor; uniform float rimK; uniform vec4 flashC;\n' + sh.fragmentShader.replace('#include <dithering_fragment>',
      `float rimF = pow(1.0 - clamp(dot(normalize(normal), normalize(vViewPosition)), 0.0, 1.0), 2.6);
       gl_FragColor.rgb += rimColor * smoothstep(0.35, 0.75, rimF) * rimK;
       gl_FragColor.rgb = mix(gl_FragColor.rgb, flashC.rgb, flashC.a);
       #include <dithering_fragment>`);
  };
}

function toonize(root, id) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = true; o.receiveShadow = false; o.frustumCulled = false;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const nm = mats.map((src) => {
      const n = (src.name || '').toLowerCase();
      const m = new THREE.MeshToonMaterial({ color: src.color.clone(), gradientMap: gradTex });
      m.name = src.name;
      if (src.vertexColors || (n === 'brain' && o.geometry.attributes.color)) m.vertexColors = true;
      if (n === 'gold') { m.color.offsetHSL(0, 0.05, 0.05); m.emissive = new THREE.Color('#5a3a00'); }
      if (n === 'glass') { m.color.set('#1a1a26'); }
      if (n === 'slime') { m.emissive = new THREE.Color('#3fbf00'); m.emissiveIntensity = 0.55; }
      if (n === 'eye' || n === 'teeth') { m.emissive = new THREE.Color('#333'); }
      m.userData.flashU = { value: new THREE.Vector4(1, 1, 1, 0) };
      m.userData.outlineParameters = { thickness: n === 'teeth' || n === 'eye' || n === 'iris' || n === 'pupil' || n === 'gem' ? 0.0025 : 0.0055, color: [0.04, 0.0, 0.08], alpha: 1 };
      rimify(m, n === 'gold' ? '#fff3b0' : '#ff5cf0', n === 'glass' ? 0.6 : 0.45);
      return m;
    });
    o.material = Array.isArray(o.material) ? nm : nm[0];
  });
}

function loadModel(id) {
  if (GLTF[id]) return Promise.resolve(GLTF[id]);
  if (LOADING[id]) return LOADING[id];
  const dl = new DRACOLoader(); dl.setDecoderPath('vendor/draco/'); dl.setDecoderConfig({ type: 'wasm' });
  const ld = new GLTFLoader(); ld.setDRACOLoader(dl);
  return LOADING[id] = new Promise((res, rej) => ld.load(MODELS[id], (g) => {
    const box = new THREE.Box3().setFromObject(g.scene); g.h = box.max.y - box.min.y;
    g.clips = {}; for (const c of g.animations) g.clips[c.name] = c;
    GLTF[id] = g; res(g);
  }, undefined, rej));
}

function makeInst(f) {
  const g = GLTF[f.id];
  const model = SkeletonUtils.clone(g.scene); toonize(model, f.id);
  const inner = new THREE.Group(); inner.add(model);
  const pivot = new THREE.Group(); pivot.add(inner);
  const s = f.F.h * (HEIGHT_K[f.id] || 1) / g.h; model.scale.setScalar(s);
  scene.add(pivot);
  const mixer = new THREE.AnimationMixer(model);
  const acts = {};
  for (const [n, c] of Object.entries(g.clips)) { const a = mixer.clipAction(c); a.enabled = true; acts[n] = a; }
  const mats = []; model.traverse((o) => { if (o.isMesh) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => mats.push(m)); });
  const I = { f, model, inner, pivot, mixer, acts, mats, cur: null, mode: '', lastSt: '', lastFlash: 0, oneShot: null, s };
  play(I, 'idle', 0);
  return I;
}

const ONCE = new Set(['jab', 'cross', 'kick', 'uppercut', 'hit', 'knockdown', 'getup', 'jump', 'airkick', 'airsmash', 'special']);
function play(I, name, fade = 0.12, restart = false) {
  const a = I.acts[name]; if (!a) return null;
  if (I.cur === name && !restart) return a;
  const prev = I.cur && I.acts[I.cur];
  a.reset(); a.paused = false; a.timeScale = 1; a.setEffectiveWeight(1);
  a.setLoop(ONCE.has(name) ? THREE.LoopOnce : THREE.LoopRepeat); a.clampWhenFinished = true;
  a.play();
  if (prev && prev !== a) { a.crossFadeFrom(prev, fade, false); }
  I.cur = name; return a;
}

const MOVE_CLIP = { L1: 'jab', L2: 'cross', L3: 'kick', H: 'uppercut', HP: 'special', GR: 'uppercut', AL: 'airkick', AH: 'airsmash' };
const sgn = (v) => (v > 0 ? 1 : v < 0 ? -1 : 0);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

function drive(I, G, dt, realDt) {
  const f = I.f, st = f.st;
  let adv = dt;   // game-time delta (0 during hit-stop)
  // hit reactions restart on every new hit
  const newHit = f.flash > I.lastFlash + 0.5; I.lastFlash = f.flash;
  const winner = (G.phase === 'ko' || G.phase === 'end') && f.side === G.winner && !f.ko;
  if (G.superF === f && G.freeze > 0) {          // special wind-up during the super freeze
    const a = play(I, 'special', 0.06); a.paused = true; a.time = clamp((0.65 - G.freeze) / 0.65, 0, 1) * 0.36; adv = realDt; I.lastSt = 'special'; return adv;
  }
  if (winner && G.koT > 0.6) { play(I, 'victory', 0.25); return dt || realDt; }
  if (st === 'attack' && f.mv) {
    const clip = MOVE_CLIP[f.mvN] || 'jab', a = play(I, clip, 0.05, I.lastSt !== 'attack' || I.lastMv !== f.mvN || f.mvT < I.lastMvT);
    const m = f.mv, tot = m.st + m.ac + m.rc, dur = a.getClip().duration; a.paused = true;
    if (f.charging) a.time = dur * (6 / 24) + Math.sin(G.time * 60) * 0.004;
    else a.time = clamp(f.mvT / tot, 0, 1) * dur * (clip === 'special' ? 0.75 : 1);
    I.lastMv = f.mvN; I.lastMvT = f.mvT;
  } else if (st === 'special') {
    const a = play(I, 'special', 0.06); a.paused = true; a.time = 0.36 + clamp(f.t, 0, 1.2) * 0.35 + (f.t > 1.0 ? (f.t - 1.0) * 0.6 : 0);
    a.time = Math.min(a.time, a.getClip().duration * 0.75);
  } else if (st === 'hitstun' || st === 'parried') {
    if (newHit || I.lastSt !== st) play(I, 'hit', 0.04, true);
  } else if (st === 'blockstun') {
    play(I, 'block', 0.05);
  } else if (st === 'block') {
    play(I, 'block', 0.08);
  } else if (st === 'launched') {
    play(I, 'launched', 0.08);
  } else if (st === 'down') {
    if (I.lastSt !== 'down') play(I, 'knockdown', 0.1, true);
  } else if (st === 'air') {
    if (I.lastSt !== 'air') play(I, 'jump', 0.06, true);
  } else if (st === 'dash') {
    play(I, 'dash', 0.06);
  } else if (st === 'walk') {
    const fwd = sgn(f.vx) === f.dir;
    const a = play(I, fwd ? 'walk' : 'walk_back', 0.12); a.paused = false; a.timeScale = clamp(Math.abs(f.vx) / 260, 0.7, 2.0);
  } else {  // idle
    if (I.lastSt === 'down' && !f.ko) { play(I, 'getup', 0.08, true); I.oneShot = 'getup'; }
    if (I.oneShot && I.cur === I.oneShot) {
      const a = I.acts[I.oneShot]; if (a.time >= a.getClip().duration - 0.02) { I.oneShot = null; play(I, 'idle', 0.15); }
    } else { I.oneShot = null; const a = play(I, 'idle', 0.15); a.paused = false; a.timeScale = 1; }
  }
  if (st !== 'idle' && I.oneShot) I.oneShot = null;
  I.lastSt = st;
  return adv;
}

function place(I, G) {
  const f = I.f, o = OVR.get(f), finD = G.fin && G.fin.d === f && !G.fin.done;
  let x = f.x, y = f.y, rot = 0, sx = 1 + f.sq, sy = 1 - f.sq, vis = true, tint = null, alpha = 1;
  if (f.st === 'launched') rot = -f.dir * clamp(0.4 + f.t * 3, 0, 1.1) * (f.ko ? 1.4 : 1) + (f.ko ? f.t * -f.dir * 6 : 0);
  if (f.st === 'hitstun') rot = -f.dir * 0.06;
  if (finD || (G.fin && G.fin.d === f)) {
    if (o) { x = o.x; y = o.y; rot = o.rot || 0; sx = o.sx; sy = o.sy; alpha = o.al == null ? 1 : o.al; if (o.sil) tint = o.sil; }
    else vis = false;
  }
  const h = f.F.h * (f.vis || 1);
  I.pivot.visible = vis && alpha > 0.05;
  I.pivot.position.set(x, y + h * 0.5, 0);
  I.pivot.rotation.set(0, 0, -rot);
  I.pivot.scale.set(sx, sy, sx);
  I.inner.position.set(0, -h * 0.5, 0);
  // facing: side-on with a slight turn toward the camera
  const want = f.dir > 0 ? Math.PI / 2 - 0.42 : -Math.PI / 2 + 0.42;
  I.model.rotation.y = want;
  I.model.scale.setScalar(I.s * (f.vis || 1));
  // flash / charge / tint
  let fc = null, fa = 0;
  if (f.flash > 0) { fc = '#ffffff'; fa = Math.min(0.6, f.flash * 0.8); }
  if (f.charging || (f.st === 'attack' && f.side === 1 && f.mv && f.mv.charge && f.mvT < f.mv.st)) { fc = '#ff2b2b'; fa = 0.3 + 0.2 * Math.sin(G.time * 40); }
  if (tint) { fc = tint; fa = 0.9 * alpha; }
  for (const m of I.mats) { const u = m.userData.flashU.value; if (fc) { const c = new THREE.Color(fc); u.set(c.r, c.g, c.b, fa); } else u.w = 0; }
}

function buildStage() {
  const tl = new THREE.TextureLoader();
  // backdrop: arena art above its floor line
  const bg = tl.load('assets/arena.webp', (t) => { t.colorSpace = THREE.SRGBColorSpace; });
  bg.wrapS = THREE.MirroredRepeatWrapping; bg.repeat.set(3, 0.74); bg.offset.set(-1, 0.26);
  const BZ = -1500, k = (D + -BZ) / D, bw = 1600 * k * 1.15, bh = 900 * 0.74 * k * 1.15;
  const back = new THREE.Mesh(new THREE.PlaneGeometry(bw * 3, bh), new THREE.MeshBasicMaterial({ map: bg, fog: false }));
  back.position.set(800, bh / 2 - 40, BZ); back.material.userData.outlineParameters = { visible: false }; scene.add(back);
  // neon floor
  const c = document.createElement('canvas'); c.width = c.height = 512; const x = c.getContext('2d');
  const g = x.createLinearGradient(0, 0, 0, 512); g.addColorStop(0, '#2a0a5c'); g.addColorStop(1, '#1a0640'); x.fillStyle = g; x.fillRect(0, 0, 512, 512);
  x.strokeStyle = '#d94dff'; x.shadowColor = '#ff5cf0'; x.shadowBlur = 18; x.lineWidth = 6; x.strokeRect(0, 0, 512, 512);
  x.lineWidth = 2; x.globalAlpha = 0.5; x.beginPath(); x.moveTo(256, 0); x.lineTo(256, 512); x.moveTo(0, 256); x.lineTo(512, 256); x.stroke();
  const ft = new THREE.CanvasTexture(c); ft.colorSpace = THREE.SRGBColorSpace; ft.wrapS = ft.wrapT = THREE.RepeatWrapping; ft.repeat.set(14, 6); ft.anisotropy = 4;
  const floorW = 7000, floorD = 1500 + D * 0.8;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(floorW, floorD, 8, 8), new THREE.MeshLambertMaterial({ map: ft, emissive: new THREE.Color('#ffffff'), emissiveMap: ft, emissiveIntensity: 0.55 }));
  floor.rotation.x = -Math.PI / 2; floor.position.set(800, 0, BZ + floorD / 2); floor.receiveShadow = true;
  floor.material.userData.outlineParameters = { visible: false }; scene.add(floor);
  // ring circle glow under the fight
  const rc = document.createElement('canvas'); rc.width = rc.height = 256; const r = rc.getContext('2d');
  r.strokeStyle = '#ff5cf0'; r.lineWidth = 6; r.shadowColor = '#ff5cf0'; r.shadowBlur = 20; r.beginPath(); r.arc(128, 128, 110, 0, 7); r.stroke(); r.globalAlpha = .5; r.beginPath(); r.arc(128, 128, 70, 0, 7); r.stroke();
  const ring = new THREE.Mesh(new THREE.PlaneGeometry(1300, 700), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(rc), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  ring.rotation.x = -Math.PI / 2; ring.position.set(800, 1, -40); ring.material.userData.outlineParameters = { visible: false }; scene.add(ring);
  // lights
  scene.add(new THREE.HemisphereLight('#c9a0ff', '#2a0b4a', 1.6));
  sun = new THREE.DirectionalLight('#ffffff', 2.2); sun.position.set(500, 1400, 900); sun.target.position.set(800, 0, 0);
  sun.castShadow = true; sun.shadow.mapSize.set(1024, 1024);
  const sc = sun.shadow.camera; sc.left = -1300; sc.right = 1300; sc.top = 900; sc.bottom = -700; sc.near = 100; sc.far = 3500; sun.shadow.bias = -0.0015; sun.shadow.normalBias = 2;
  scene.add(sun); scene.add(sun.target);
  const fill = new THREE.DirectionalLight('#7fd8ff', 0.7); fill.position.set(1600, 600, 400); scene.add(fill);
}

function init() {
  cv3 = document.createElement('canvas'); cv3.id = 'cv3';
  cv3.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;display:block;touch-action:none;z-index:0;pointer-events:none';
  const cv = document.getElementById('cv'); cv.parentNode.insertBefore(cv3, cv);
  renderer = new THREE.WebGLRenderer({ canvas: cv3, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.6));
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  scene = new THREE.Scene();
  { const c = document.createElement('canvas'); c.width = 4; c.height = 256; const x = c.getContext('2d'); const g = x.createLinearGradient(0, 0, 0, 256);
    g.addColorStop(0, '#05000f'); g.addColorStop(0.55, '#140433'); g.addColorStop(1, '#1d0646'); x.fillStyle = g; x.fillRect(0, 0, 4, 256);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; scene.background = t; }
  camera = new THREE.PerspectiveCamera(30, 1, 10, 20000);
  effect = new OutlineEffect(renderer, { defaultThickness: 0.005, defaultColor: [0.04, 0, 0.08] });
  gradTex = toonGradient();
  buildStage();
  const rs = () => renderer.setSize(innerWidth, innerHeight, false);
  addEventListener('resize', rs); rs();
  Promise.all(Object.keys(MODELS).map(loadModel)).then(() => { ready = true; window.dispatchEvent(new Event('r3d-ready')); }).catch((e) => console.error('3D load failed', e));
}

function setCamera(VIEW, shx, shy) {
  const W = innerWidth, H = innerHeight, s = VIEW.s, cx = VIEW.cx - shx / s, fy = VIEW.fy + shy;
  const Yc = 150 + D * ELEV;
  camera.position.set(cx, Yc, D); camera.rotation.set(0, 0, 0); camera.updateMatrixWorld();
  const n = camera.near, k = n / D;
  const L = -W / (2 * s) * k, R = W / (2 * s) * k, T = (fy / s - Yc) * k, B = ((fy - H) / s - Yc) * k;
  camera.projectionMatrix.makePerspective(L, R, T, B, n, camera.far);
  camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
}

const R3D = {
  ids: Object.keys(MODELS),
  isReady: () => ready,
  supports: (id) => !!MODELS[id],
  has(f) { return ready && f && !!MODELS[f.id] && INST.has(f); },
  over(f, o) { OVR.set(f, o); },
  active: () => ready,
  clearOver() { OVR.clear(); },
  render(G, VIEW, shx = 0, shy = 0) {
    if (!ready || !G) return;
    // (re)bind fighter instances
    for (const [f, I] of INST) if (f !== G.p1 && f !== G.p2) { scene.remove(I.pivot); INST.delete(f); }
    for (const f of [G.p1, G.p2]) if (f && MODELS[f.id] && GLTF[f.id] && !INST.has(f)) INST.set(f, makeInst(f));
    const now = performance.now() / 1000, realDt = lastReal ? Math.min(0.05, now - lastReal) : 0; lastReal = now;
    const gdt = lastGT < 0 || G.time < lastGT ? 0 : Math.min(0.05, G.time - lastGT); lastGT = G.time;
    for (const I of INST.values()) { const adv = drive(I, G, gdt, realDt); I.mixer.update(adv); place(I, G); }
    setCamera(VIEW, shx, shy);
    sun.position.set(VIEW.cx - 300, 1400, 900); sun.target.position.set(VIEW.cx, 0, 0);
    effect.render(scene, camera);
    OVR.clear();
  },
  // debug / previews
  _t: { THREE, get scene() { return scene; }, get camera() { return camera; }, get renderer() { return renderer; }, INST, GLTF, get effect() { return effect; }, loadModel, toonize, makeInst },
};
window.R3D = R3D;
init();
