# Shared Blender helpers for Brainrot Battle 3D fighters (run inside blender -b -P)
import bpy, bmesh, math, os
from mathutils import Vector, Euler, Matrix, Quaternion
D = bpy.data
rad = math.radians

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in (D.meshes, D.materials, D.objects): pass

def hex2lin(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]

def mat(name, hexcol, rough=0.6, metal=0.0, emit=0.0):
    m = D.materials.get(name)
    if m: return m
    m = D.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; c = hex2lin(hexcol)
    b.inputs['Base Color'].default_value = (*c, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*c, 1)
        b.inputs['Emission Strength'].default_value = emit
    m.diffuse_color = (*c, 1)
    return m

def link(ob):
    bpy.context.scene.collection.objects.link(ob); return ob

def activate(ob, sel=None):
    for o in bpy.context.scene.objects: o.select_set(False)
    for o in (sel or [ob]): o.select_set(True)
    bpy.context.view_layer.objects.active = ob

_mbn = [0]
def meta(elems, res=0.022, thresh=0.6, name=None):
    """elems: list of dict(co, r, s=(sx,sy,sz), rot=(deg xyz), t='ELLIPSOID'|'BALL'|'CAPSULE', k=stiffness, neg)"""
    _mbn[0] += 1; nm = name or ('MB%03d' % _mbn[0])
    mb = D.metaballs.new(nm); mb.resolution = res; mb.render_resolution = res; mb.threshold = thresh
    for e in elems:
        el = mb.elements.new(type=e.get('t', 'ELLIPSOID'))
        el.co = Vector(e['co']); el.radius = e['r']
        if 's' in e: el.size_x, el.size_y, el.size_z = e['s']
        if 'rot' in e: el.rotation = Euler([rad(a) for a in e['rot']]).to_quaternion()
        if 'q' in e: el.rotation = e['q']
        el.stiffness = e.get('k', 2.0)
        if e.get('neg'): el.use_negative = True
    ob = link(D.objects.new(nm, mb)); activate(ob)
    bpy.context.view_layer.update()
    bpy.ops.object.convert(target='MESH')
    me = bpy.context.view_layer.objects.active
    me.name = nm + '_mesh'
    return me

def cap(a, b, r, k=8.0, neg=False):
    a, b = Vector(a), Vector(b); d = b - a
    e = dict(t='CAPSULE', co=(a + b) / 2, r=r * 1.3, s=(d.length / 2, 1, 1), q=Vector((1, 0, 0)).rotation_difference(d), k=k)
    if neg: e['neg'] = True
    return e

def ell(co, s, r=1.0, rot=None, k=8.0, neg=False):
    e = dict(t='ELLIPSOID', co=co, r=r * 1.3, s=s, k=k)
    if rot: e['rot'] = rot
    if neg: e['neg'] = True
    return e

def ball(co, r, k=8.0):
    return dict(t='BALL', co=co, r=r * 1.3, k=k)

def apply_mods(ob):
    activate(ob)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)

def remesh(ob, voxel=0.018, smooth=0, csmooth=0, fac=0.5):
    m = ob.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = voxel; m.adaptivity = 0
    if smooth:
        s = ob.modifiers.new('sm', 'SMOOTH'); s.iterations = smooth; s.factor = fac
    if csmooth:
        s = ob.modifiers.new('lap', 'LAPLACIANSMOOTH'); s.iterations = csmooth; s.lambda_factor = 0.5
    apply_mods(ob)
    return ob

def shade_smooth(ob, angle=None):
    for p in ob.data.polygons: p.use_smooth = True

def set_mat(ob, m):
    ob.data.materials.clear(); ob.data.materials.append(m)

def add_mat(ob, m):
    if m.name not in [x.name for x in ob.data.materials if x]: ob.data.materials.append(m)
    return [x.name for x in ob.data.materials].index(m.name)

def paint_faces(ob, m, fn):
    """assign material m to faces whose center (object space) and normal satisfy fn(c, n)"""
    i = add_mat(ob, m)
    for p in ob.data.polygons:
        if fn(p.center, p.normal): p.material_index = i

def prim(kind, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), **kw):
    if kind == 'sphere': bpy.ops.mesh.primitive_uv_sphere_add(segments=kw.get('seg', 24), ring_count=kw.get('rings', 12), location=loc)
    elif kind == 'ico': bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=kw.get('sub', 3), location=loc)
    elif kind == 'cube': bpy.ops.mesh.primitive_cube_add(location=loc)
    elif kind == 'cyl': bpy.ops.mesh.primitive_cylinder_add(vertices=kw.get('seg', 16), location=loc)
    elif kind == 'cone': bpy.ops.mesh.primitive_cone_add(vertices=kw.get('seg', 12), radius1=kw.get('r1', 1), radius2=kw.get('r2', 0), depth=kw.get('depth', 2), location=loc)
    elif kind == 'torus': bpy.ops.mesh.primitive_torus_add(major_radius=kw.get('R', 1), minor_radius=kw.get('r', .25), major_segments=kw.get('seg', 24), minor_segments=kw.get('mseg', 8), location=loc)
    ob = bpy.context.view_layer.objects.active
    ob.scale = scale; ob.rotation_euler = [rad(a) for a in rot]
    activate(ob); bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return ob

def bevel(ob, w=0.02, seg=3):
    m = ob.modifiers.new('bv', 'BEVEL'); m.width = w; m.segments = seg; m.limit_method = 'ANGLE'
    return ob

def subsurf(ob, lv=2):
    m = ob.modifiers.new('ss', 'SUBSURF'); m.levels = lv; m.render_levels = lv
    return ob

def poly_extrude(pts2d, depth, plane='XZ', name='poly'):
    """pts2d: list of (u,v) outline; plane XZ extrudes along Y (centered); returns mesh object"""
    bm = bmesh.new()
    vs = []
    for u, v in pts2d:
        co = Vector((u, -depth / 2, v)) if plane == 'XZ' else (Vector((-depth / 2, u, v)) if plane == 'YZ' else Vector((u, v, -depth / 2)))
        vs.append(bm.verts.new(co))
    f = bm.faces.new(vs)
    axis = Vector((0, depth, 0)) if plane == 'XZ' else (Vector((depth, 0, 0)) if plane == 'YZ' else Vector((0, 0, depth)))
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=nv, vec=axis)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = link(D.objects.new(name, me)); activate(ob)
    return ob

def join(objs, name=None):
    activate(objs[0], objs); bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    if name: ob.name = name
    return ob

def boolean(ob, cutter, op='DIFFERENCE', transfer=True):
    m = ob.modifiers.new('bool', 'BOOLEAN'); m.operation = op; m.object = cutter; m.solver = 'EXACT'
    if transfer: m.material_mode = 'TRANSFER'
    apply_mods(ob); D.objects.remove(cutter)

def ray_surface(ob, origin, direction):
    """ray cast against ob (object space == world space here, objects are unparented with identity transforms)"""
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nrm, idx = ob.evaluated_get(dg).ray_cast(Vector(origin), Vector(direction).normalized())
    return (loc, nrm) if hit else (None, None)

def align_to_normal(ob, nrm, up=Vector((0, 0, 1))):
    """rotate ob so its local -Y faces along nrm"""
    q = Vector((0, -1, 0)).rotation_difference(nrm)
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = q

def decimate(ob, ratio):
    m = ob.modifiers.new('dec', 'DECIMATE'); m.ratio = ratio; apply_mods(ob)

def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)

# ------------------------------------------------------------------ RIG
# Standard bone set shared by all humanoid fighters
def build_rig(J, extra=()):
    """J: dict of joint name -> Vector. Required: root, hips, spine, chest, neck, head, head_top,
    shoulder_L/R, elbow_L/R, wrist_L/R, hand_tip_L/R, hip_L/R, knee_L/R, ankle_L/R, toe_L/R"""
    arm = D.armatures.new('Armature'); ob = link(D.objects.new('Armature', arm))
    activate(ob); bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    def bone(n, h, t, par=None, con=False):
        b = eb.new(n); b.head = Vector(h); b.tail = Vector(t)
        if par: b.parent = eb[par]; b.use_connect = con
        return b
    bone('root', J['root'], J['root'] + Vector((0, 0.3, 0)))
    bone('hips', J['hips'], J['spine'], 'root')
    bone('spine', J['spine'], J['chest'], 'hips', True)
    bone('chest', J['chest'], J['neck'], 'spine', True)
    bone('neck', J['neck'], J['head'], 'chest', True)
    bone('head', J['head'], J['head_top'], 'neck', True)
    for s in 'LR':
        bone('upper_arm.' + s, J['shoulder_' + s], J['elbow_' + s], 'chest')
        bone('forearm.' + s, J['elbow_' + s], J['wrist_' + s], 'upper_arm.' + s, True)
        bone('hand.' + s, J['wrist_' + s], J['hand_tip_' + s], 'forearm.' + s, True)
        bone('thigh.' + s, J['hip_' + s], J['knee_' + s], 'hips')
        bone('shin.' + s, J['knee_' + s], J['ankle_' + s], 'thigh.' + s, True)
        bone('foot.' + s, J['ankle_' + s], J['toe_' + s], 'shin.' + s, True)
    for (n, h, t, par, con) in extra: bone(n, h, t, par, con)
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in ob.pose.bones: pb.rotation_mode = 'QUATERNION'
    return ob

def skin(body, rig):
    activate(rig, [body, rig]); bpy.ops.object.parent_set(type='ARMATURE_AUTO')

def rigid(ob, bone, w=1.0):
    vg = ob.vertex_groups.new(name=bone); vg.add(list(range(len(ob.data.vertices))), w, 'REPLACE')
    return ob

def rigid_by(ob, fn):
    """fn(co) -> list of (bone, weight)"""
    groups = {}
    for v in ob.data.vertices:
        for b, w in fn(v.co):
            if b not in groups: groups[b] = ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)
            groups[b].add([v.index], w, 'REPLACE')

# ------------------------------------------------------------------ ANIMATION
ORDER = ['root', 'hips', 'spine', 'chest', 'neck', 'head', 'upper_arm.L', 'forearm.L', 'hand.L', 'upper_arm.R', 'forearm.R', 'hand.R',
         'thigh.L', 'shin.L', 'foot.L', 'thigh.R', 'shin.R', 'foot.R']
REF = {'upper_arm': 'chest', 'forearm': 'chest', 'hand': 'chest', 'thigh': 'hips', 'shin': 'hips', 'foot': 'hips'}

def mirror_spec(spec):
    """swap L/R and mirror X in directions / eulers (y,z rot negate)"""
    out = {}
    for k, v in spec.items():
        nk = k.replace('.L', '.#').replace('.R', '.L').replace('.#', '.R')
        if v[0] == 'd': out[nk] = ('d', (-v[1][0], v[1][1], v[1][2]))
        elif v[0] == 'e': out[nk] = ('e', (v[1][0], -v[1][1], -v[1][2]))
        elif v[0] == 'l': out[nk] = ('l', (-v[1][0], v[1][1], v[1][2]))
        else: out[nk] = v
    return out

class Animator:
    def __init__(self, rig, scale=1.0, amp=None):
        self.rig = rig; self.S = scale
        self.R = {b.name: b.matrix_local.to_quaternion() for b in rig.data.bones}
        self.dir0 = {b.name: (b.tail_local - b.head_local).normalized() for b in rig.data.bones}
        self.par = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
        self.bones = [b.name for b in rig.data.bones]
        self.order = [n for n in ORDER if n in self.bones] + [n for n in self.bones if n not in ORDER]
        self.head = {b.name: b.head_local.copy() for b in rig.data.bones}
        self.L = {b.name: b.length for b in rig.data.bones}
        self.ankle0 = {s: rig.data.bones['shin.' + s].tail_local.copy() for s in 'LR'}

    def solve(self, spec):
        """spec keys: bone -> ('e',(x,y,z)) armature-axis degrees | ('d',dir in ref frame) | ('dr', dir in root frame)
        'bone@loc' -> ('l', armature-axis offset); 'armik.L' -> (frame 'chest'|'root', offset from shoulder, pole)
        'legik.L' -> (offset of ankle from rest ankle in root frame, pole)"""
        Q = {}; P = {}; out = {}; ikd = {}
        H = self.head
        for n in self.order:
            p = self.par[n]; Qp = Q[p] if p else Quaternion()
            q = Quaternion(); loc = Vector()
            if n + '@loc' in spec: loc = Vector(spec[n + '@loc'][1]) * self.S
            P[n] = (P[p] + Qp @ (H[n] - H[p]) if p else H[n].copy()) + Qp @ loc
            side = n[-1] if n[-2:] in ('.L', '.R') else None
            base = n.split('.')[0]
            if base == 'upper_arm' and ('armik.' + side) in spec:
                fr, off, pole = spec['armik.' + side]
                Qf = Q['chest'] if fr == 'chest' else Q['root']
                tgt = P[n] + Qf @ (Vector(off) * self.S)
                d1, d2 = self._two_bone(P[n], tgt, self.L[n], self.L['forearm.' + side], Qf @ Vector(pole))
                ikd[n] = d1; ikd['forearm.' + side] = d2
            if base == 'thigh' and ('legik.' + side) in spec:
                off, pole = spec['legik.' + side]
                Qr = Q['root']
                tgt = P['root'] + Qr @ (self.ankle0[side] - H['root'] + Vector(off) * self.S)
                d1, d2 = self._two_bone(P[n], tgt, self.L[n], self.L['shin.' + side], Qr @ Vector(pole))
                ikd[n] = d1; ikd['shin.' + side] = d2
            v = spec.get(n)
            if n in ikd and not v:
                want = Qp.inverted() @ ikd[n]
                q = self.dir0[n].rotation_difference(want)
            elif v:
                if v[0] == 'e':
                    q = Euler([rad(a) for a in v[1]], 'XYZ').to_quaternion()
                elif v[0] in ('d', 'dr'):
                    ref = 'root' if v[0] == 'dr' else REF.get(base, p)
                    Qr = Q.get(ref, Quaternion())
                    want = (Qp.inverted() @ Qr) @ Vector(v[1]).normalized()
                    q = self.dir0[n].rotation_difference(want)
            Q[n] = Qp @ q
            R = self.R[n]
            out[n] = (R.inverted() @ q @ R, R.inverted() @ loc)
        return out

    def _two_bone(self, a, tgt, la, lb, pole):
        t = tgt - a; d = t.length
        d = max(min(d, (la + lb) * 0.999), abs(la - lb) * 1.01 + 1e-4)
        tn = t.normalized()
        cosA = (la * la + d * d - lb * lb) / (2 * la * d); cosA = max(-1, min(1, cosA))
        pp = pole - tn * pole.dot(tn)
        if pp.length < 1e-6: pp = Vector((0, -1, 0))
        pp.normalize()
        A = math.acos(cosA)
        d1 = tn * math.cos(A) + pp * math.sin(A)
        knee = a + d1 * la
        d2 = (a + tn * d - knee).normalized()
        return d1, d2

    def action(self, name, keys, loop=False, fps=30):
        """keys: list of (frame, spec). For loops last frame should equal first."""
        rig = self.rig
        act = D.actions.new(name); rig.animation_data_create(); rig.animation_data.action = act
        for f, spec in keys:
            sol = self.solve(spec)
            for n, (q, l) in sol.items():
                pb = rig.pose.bones[n]
                pb.rotation_quaternion = q; pb.location = l
                pb.keyframe_insert('rotation_quaternion', frame=f, group=n)
                pb.keyframe_insert('location', frame=f, group=n)
        # make quaternion keys continuous handled by gltf; set interpolation
        for fc in act.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'
        tr = rig.animation_data.nla_tracks.new(); tr.name = name
        st = tr.strips.new(name, int(keys[0][0]), act); st.name = name
        rig.animation_data.action = None
        act.use_fake_user = True
        return act

def export_glb(path, objs):
    activate(objs[0], objs)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
        export_draco_position_quantization=14, export_draco_normal_quantization=10,
        export_animations=True, export_animation_mode='ACTIONS', export_nla_strips=True,
        export_force_sampling=True, export_frame_step=1, export_optimize_animation_size=True,
        export_skins=True, export_all_influences=False, export_apply=True, export_yup=True,
        export_texcoords=False, export_normals=True, export_morph=False)

def render_preview(path, objs, views=((0, -6, 1.2),), size=(520, 600), target=(0, 0, 1.0), lens=90, engine='BLENDER_WORKBENCH'):
    sc = bpy.context.scene
    sc.render.engine = engine; sc.render.resolution_x, sc.render.resolution_y = size
    if engine == 'BLENDER_WORKBENCH':
        sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
        sc.display.shading.show_cavity = True; sc.display.shading.show_object_outline = True
    sc.render.film_transparent = False
    if 'PrevCam' not in D.objects:
        cam = link(D.objects.new('PrevCam', D.cameras.new('PrevCam')))
    cam = D.objects['PrevCam']; cam.data.lens = lens; sc.camera = cam
    paths = []
    for i, v in enumerate(views):
        cam.location = Vector(v)
        d = Vector(target) - cam.location
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        p = path.replace('.png', '_%d.png' % i); sc.render.filepath = p
        bpy.ops.render.render(write_still=True); paths.append(p)
    return paths

# ------------------------------------------------------------------ surface-conforming shells (glasses, patches)
def shell(body, O, U, V, Dv, inside, ur, vr, res, off, thick, m, name='shell', smooth_iter=2):
    O, U, V, Dv = Vector(O), Vector(U).normalized(), Vector(V).normalized(), Vector(Dv).normalized()
    dg = bpy.context.evaluated_depsgraph_get(); be = body.evaluated_get(dg)
    nu = int((ur[1] - ur[0]) / res) + 1; nv = int((vr[1] - vr[0]) / res) + 1
    bm = bmesh.new(); grid = {}
    for i in range(nu):
        for j in range(nv):
            u = ur[0] + i * res; v = vr[0] + j * res
            if not inside(u, v): continue
            o = O + U * u + V * v - Dv * 3
            hit, loc, nrm, _ = be.ray_cast(o, Dv)
            if hit: grid[(i, j)] = bm.verts.new(loc + nrm * off)
    for i in range(nu - 1):
        for j in range(nv - 1):
            q = [grid.get(k) for k in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
            if all(q): bm.faces.new(q)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for v in [v for v in bm.verts if not v.link_faces]: bm.verts.remove(v)
    me = D.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = link(D.objects.new(name, me))
    if smooth_iter:
        s = ob.modifiers.new('sm', 'SMOOTH'); s.iterations = smooth_iter; s.factor = 0.5
    so = ob.modifiers.new('sol', 'SOLIDIFY'); so.thickness = thick; so.offset = 1
    bv = ob.modifiers.new('bv', 'BEVEL'); bv.width = min(thick * 0.4, 0.01); bv.segments = 2
    apply_mods(ob); set_mat(ob, m); shade_smooth(ob)
    return ob

def transfer_weights(src, dst):
    for g in src.vertex_groups:
        if g.name not in dst.vertex_groups: dst.vertex_groups.new(name=g.name)
    m = dst.modifiers.new('dt', 'DATA_TRANSFER'); m.object = src
    m.use_vert_data = True; m.data_types_verts = {'VGROUP_WEIGHTS'}; m.vert_mapping = 'POLYINTERP_NEAREST'
    m.layers_vgroup_select_src = 'ALL'; m.layers_vgroup_select_dst = 'NAME'
    activate(dst); bpy.ops.object.modifier_apply(modifier=m.name)
