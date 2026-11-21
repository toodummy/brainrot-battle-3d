# Keyframe animation library shared by all humanoid fighters.
# Blender coords: character faces -Y, up +Z, character's left = +X.
from b3d_common import Animator, mirror_spec
import math

def M(*dicts):
    o = {}
    for d in dicts: o.update(d)
    return o

AP_L = (0.8, 0.5, -1.0); AP_R = (-0.8, 0.5, -1.0)   # elbow poles (down/out/back)
LP_L = (0.12, -1, 0.0); LP_R = (-0.12, -1, 0.0)      # knee poles (forward)
FOOT = ('dr', (0, -1, -0.28))

def legs(lo=(0.03, -0.07, 0), ro=(-0.03, 0.07, 0), lf=FOOT, rf=FOOT):
    return {'legik.L': (lo, LP_L), 'legik.R': (ro, LP_R), 'foot.L': lf, 'foot.R': rf}

def arms(l, r, fr='chest', lp=AP_L, rp=AP_R):
    return {'armik.L': (fr, l, lp), 'armik.R': (fr, r, rp)}

GUARD_L = (-0.13, -0.36, 0.10); GUARD_R = (0.11, -0.30, 0.06)

def guard(drop=0.07, breathe=0.0, twist=-8, armz=0.0):
    return M({'hips@loc': ('l', (0, 0, -drop)), 'hips': ('e', (0, 0, twist * 0.5)),
              'spine': ('e', (6 + breathe * 2, 0, twist * 0.5)), 'chest': ('e', (4 - breathe * 3, 0, 0)),
              'neck': ('e', (-4, 0, -twist * 0.4)), 'head': ('e', (-6 + breathe, 0, -twist * 0.4))},
             arms((GUARD_L[0], GUARD_L[1], GUARD_L[2] + armz), (GUARD_R[0], GUARD_R[1], GUARD_R[2] + armz)),
             legs())

def tail(sw, lift=0):
    return {'tail1': ('e', (lift, 0, sw)), 'tail2': ('e', (lift * 0.6, 0, sw * 1.4))}

def make_all(rig, style='shark', S=1.0):
    global GUARD_L, GUARD_R
    if style == 'boss': GUARD_L = (-0.10, -0.40, -0.16); GUARD_R = (0.08, -0.34, -0.22)
    A = Animator(rig, scale=S)
    has_tail = 'tail1' in A.bones
    T = (lambda sw, lift=0: tail(sw, lift)) if has_tail else (lambda sw, lift=0: {})
    G = guard

    # IDLE (loop)
    A.action('idle', [
        (0, M(G(0.07, 0), T(10))),
        (20, M(G(0.10, 1.0, armz=-0.03), T(-10, 4))),
        (40, M(G(0.07, 0), T(10))),
    ])
    # WALK forward (loop 24f) / back
    def walk_keys(sign):
        st = 0.17
        k = []
        seq = [(0, -st, st, 0, 0, 0.09), (6, 0, 0, 0, 0.13, 0.05), (12, st, -st, 0, 0, 0.09), (18, 0, 0, 0.13, 0, 0.05), (24, -st, st, 0, 0, 0.09)]
        for f, ly, ry, lz, rz, drop in seq:
            g = G(drop, 0, twist=-8 + (8 if ly < 0 else -8 if ly > 0 else 0))
            g.update(legs((0.03, ly * sign + (0.02 if lz else 0), lz), (-0.03, ry * sign + (0.02 if rz else 0), rz)))
            g['spine'] = ('e', (10 * sign, 0, -4)); g.update(T(12 if f % 12 == 0 else -12))
            k.append((f, g))
        return k
    A.action('walk', walk_keys(1))
    wb = walk_keys(1); A.action('walk_back', [(24 - f, sp) for f, sp in reversed(wb)])
    # DASH (lunge pose)
    dash = M(G(0.14, 0), legs((0.03, -0.30, 0.0), (-0.03, 0.32, 0.08), rf=('dr', (0, -0.4, -1))))
    dash['spine'] = ('e', (22, 0, 0)); dash['head'] = ('e', (-22, 0, 0)); dash.update(arms((-0.05, -0.3, -0.1), (0.15, 0.25, -0.15)))
    A.action('dash', [(0, dash), (8, M(dash, T(-15)))])

    # JAB (left lead) 14f
    jab = M(G(0.08), arms((-0.04, -0.72, 0.12), GUARD_R, 'root'))
    jab['chest'] = ('e', (6, 0, -22)); jab['spine'] = ('e', (10, 0, -8)); jab['head'] = ('e', (-8, 0, 20))
    A.action('jab', [(0, G()), (3, jab), (6, jab), (14, G())])
    # CROSS (right) 15f
    cross = M(G(0.10), arms((-0.18, -0.28, 0.08), (0.06, -0.78, 0.10), 'root'), legs(ro=(-0.03, 0.12, 0), rf=('dr', (0.3, -1, -0.5))))
    cross['chest'] = ('e', (8, 0, 30)); cross['spine'] = ('e', (12, 0, 12)); cross['hips'] = ('e', (0, 0, 14)); cross['head'] = ('e', (-10, 0, -30))
    A.action('cross', [(0, G()), (4, cross), (7, cross), (15, G())])
    # KICK (right front kick) 15f
    chamber = M(G(0.06), legs(ro=(-0.02, -0.22, 0.32), rf=('dr', (0, -1, 0.3))))
    chamber['spine'] = ('e', (-6, 0, 0))
    kick = M(G(0.04), legs(ro=(-0.02, -0.62, 0.42), rf=('dr', (0, -1, 0.5))), arms((-0.05, -0.3, 0.0), (0.25, 0.15, -0.2)))
    kick['spine'] = ('e', (-18, 0, 0)); kick['chest'] = ('e', (-4, 0, 0)); kick['head'] = ('e', (14, 0, 0))
    A.action('kick', [(0, G()), (3, chamber), (6, kick), (9, kick), (15, G())])
    # UPPERCUT (heavy, wind-up) 24f
    wind = M(G(0.20), arms(GUARD_L, (0.05, 0.12, -0.42), 'chest'), legs((0.05, -0.12, 0), (-0.05, 0.12, 0)))
    wind['spine'] = ('e', (18, 0, 25)); wind['chest'] = ('e', (6, 0, 15)); wind['head'] = ('e', (-20, 0, -25)); wind.update(T(-20))
    upc = M(G(-0.04), arms((-0.12, -0.30, 0.0), (-0.02, -0.38, 0.62), 'root', rp=(-0.6, 0.6, -0.4)), legs((0.03, -0.1, 0.0), (-0.03, 0.12, 0.06), rf=('dr', (0, -0.3, -1))))
    upc['spine'] = ('e', (-14, 0, -20)); upc['chest'] = ('e', (-6, 0, -15)); upc['head'] = ('e', (-24, 0, 10)); upc.update(T(20, 10))
    A.action('uppercut', [(0, G()), (6, wind), (9, upc), (13, upc), (24, G())])
    # BLOCK (hold)
    blk = M(G(0.14), arms((0.06, -0.30, 0.22), (-0.06, -0.34, 0.14), 'chest'))
    blk['spine'] = ('e', (14, 0, 0)); blk['head'] = ('e', (12, 0, 0))
    blk2 = M(blk, {'hips@loc': ('l', (0, 0, -0.155))})
    A.action('block', [(0, blk), (15, blk2), (30, blk)])
    # HIT react 12f
    hit = M(G(0.06), arms((0.18, -0.05, -0.05), (-0.20, 0.0, -0.1), 'chest'), legs(lo=(0.03, -0.02, 0.06)))
    hit['hips@loc'] = ('l', (0, 0.06, -0.06)); hit['spine'] = ('e', (-16, 0, 6)); hit['chest'] = ('e', (-14, 0, 0))
    hit['neck'] = ('e', (-14, 0, 0)); hit['head'] = ('e', (-26, 0, 12)); hit.update(T(-25, 15))
    A.action('hit', [(0, G()), (2, hit), (5, hit), (12, G())])
    # LAUNCHED (airborne hurt, loop-ish)
    lau = M(G(0.0), arms((0.35, 0.1, 0.25), (-0.35, 0.15, 0.3), 'chest'), legs((0.06, -0.25, 0.25), (-0.06, -0.10, 0.12), lf=('dr', (0, -1, 0.4)), rf=('dr', (0, -1, 0.2))))
    lau['spine'] = ('e', (-24, 0, 0)); lau['chest'] = ('e', (-12, 0, 0)); lau['head'] = ('e', (-30, 0, 0)); lau.update(T(25, 20))
    lau2 = M(lau, arms((0.38, 0.0, 0.40), (-0.32, 0.2, 0.15), 'chest')); lau2.update(T(-25, 20))
    A.action('launched', [(0, lau), (8, lau2), (16, lau)])
    # KNOCKDOWN: fall to back and lie
    down = M(G(0.0), arms((0.42, 0.05, -0.05), (-0.42, 0.0, 0.05), 'chest'), legs((0.06, -0.05, 0.18), (-0.06, 0.05, 0.10), lf=('dr', (0, 0, 1)), rf=('dr', (0.2, 0, 1))))
    down['root'] = ('e', (-90, 0, 0)); down['root@loc'] = ('l', (0, -0.95, 0.34)); down['hips@loc'] = ('l', (0, 0, 0))
    down['spine'] = ('e', (-4, 0, 0)); down['head'] = ('e', (-10, 0, 20)); down.update(T(0, -60))
    bounce = M(down, {'root@loc': ('l', (0, -0.95, 0.42)), 'root': ('e', (-84, 0, 0))})
    A.action('knockdown', [(0, M(lau, {'root': ('e', (-30, 0, 0))})), (7, down), (10, bounce), (14, down), (30, down)])
    # GET UP 20f
    sit = M(G(0.0), arms((0.2, -0.1, -0.35), (-0.2, -0.1, -0.35), 'chest'), legs((0.06, -0.35, 0.0), (-0.06, -0.15, 0.0)))
    sit['root'] = ('e', (-50, 0, 0)); sit['root@loc'] = ('l', (0, -0.5, 0.22)); sit['spine'] = ('e', (35, 0, 0)); sit['head'] = ('e', (-10, 0, 0))
    crouch = M(G(0.32), legs((0.06, -0.1, 0), (-0.06, 0.12, 0)), arms((0.0, -0.3, -0.2), (0.0, -0.3, -0.25), 'chest'))
    crouch['spine'] = ('e', (30, 0, 0)); crouch['head'] = ('e', (-25, 0, 0))
    A.action('getup', [(0, down), (7, sit), (13, crouch), (20, G())])
    # JUMP 16f
    pre = M(G(0.22)); pre['spine'] = ('e', (16, 0, 0))
    air = M(G(0.0), legs((0.03, -0.12, 0.30), (-0.03, 0.05, 0.22), lf=('dr', (0, -1, 0.1)), rf=('dr', (0, -1, 0.0))), arms((-0.1, -0.3, 0.25), (0.12, -0.25, 0.2), 'chest'))
    air['spine'] = ('e', (10, 0, 0)); air.update(T(15, 15))
    A.action('jump', [(0, pre), (4, M(G(-0.05), legs(lf=('dr', (0, -0.2, -1)), rf=('dr', (0, -0.2, -1))))), (10, air), (16, air)])
    # AIR KICK 12f (light air) / AIR SMASH (heavy air)
    ak = M(air, legs((0.03, -0.12, 0.30), (-0.02, -0.60, 0.25), lf=('dr', (0, -1, 0.1)), rf=('dr', (0, -1, 0.6))))
    ak['spine'] = ('e', (-14, 0, 0))
    A.action('airkick', [(0, air), (3, ak), (9, ak), (12, air)])
    smu = M(air, arms((0.05, -0.05, 0.55), (-0.05, -0.05, 0.55), 'chest', AP_L, AP_R)); smu['spine'] = ('e', (-16, 0, 0)); smu['head'] = ('e', (-10, 0, 0))
    smd = M(air, arms((-0.05, -0.55, -0.35), (0.05, -0.55, -0.35), 'chest')); smd['spine'] = ('e', (30, 0, 0)); smd['head'] = ('e', (-30, 0, 0))
    A.action('airsmash', [(0, air), (5, smu), (8, smd), (14, smd), (18, air)])
    # SPECIAL: wind-up (charge) + release, 32f
    sw = M(G(0.22), arms((0.30, 0.22, -0.30), (-0.30, 0.22, -0.30), 'chest'), legs((0.08, -0.15, 0), (-0.08, 0.15, 0)))
    sw['spine'] = ('e', (-12, 0, 0)); sw['chest'] = ('e', (-10, 0, 0)); sw['head'] = ('e', (-18, 0, 0)); sw.update(T(25, 20))
    sw2 = M(sw, {'hips@loc': ('l', (0, 0, -0.25))}); sw2.update(arms((0.34, 0.26, -0.26), (-0.34, 0.26, -0.26), 'chest'))
    rel = M(G(0.12), arms((-0.05, -0.80, 0.10), (0.05, -0.80, 0.10), 'root', (0.9, 0.3, 0.2), (-0.9, 0.3, 0.2)), legs((0.06, -0.30, 0), (-0.06, 0.30, 0), rf=('dr', (0, -0.4, -1))))
    rel['spine'] = ('e', (22, 0, 0)); rel['chest'] = ('e', (6, 0, 0)); rel['head'] = ('e', (-24, 0, 0)); rel.update(T(-25))
    A.action('special', [(0, G()), (5, sw), (10, sw2), (13, rel), (24, rel), (32, G())])
    # VICTORY loop 40f (double biceps flex + bounce)
    def flex(h, up):
        v = M(G(h), arms((0.40, 0.02, 0.10 + up), (-0.40, 0.02, 0.10 + up), 'chest', (0.2, 0.3, -1), (-0.2, 0.3, -1)))
        v['spine'] = ('e', (-8, 0, 0)); v['chest'] = ('e', (-8, 0, 0)); v['head'] = ('e', (-18, 0, 0)); v['hips'] = ('e', (0, 0, 0)); v.update(T(18 if up else -18, 10))
        v.update(legs((0.06, 0, 0), (-0.06, 0, 0)))
        return v
    A.action('victory', [(0, flex(0.04, 0)), (10, flex(0.12, 0.08)), (20, flex(0.04, 0)), (30, flex(0.12, 0.08)), (40, flex(0.04, 0))])
