import sys; sys.path.insert(0,'/workspace/brainrot-battle-3d/tools')
from b3d_common import *
from mathutils import noise
import random
reset(); random.seed(7)
OUT = sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else '/workspace/b3d/boss.glb'
M = dict(skin=mat('skin','#7d2fd0',0.55), skind=mat('skindark','#5a1fa0',0.6), brain=mat('brain','#ff7cc8',0.45),
 face=mat('face','#d23d9c',0.5), mouth=mat('mouth','#4a0b2a',0.8), teeth=mat('teeth','#fff3cf',0.3),
 eye=mat('eye','#fffbe8',0.2), iris=mat('iris','#6b3a12',0.3), pupil=mat('pupil','#0d0508',0.2),
 gold=mat('gold','#ffc22e',0.3,1.0), gem=mat('gem','#ff2d7a',0.2), slime=mat('slime','#9dff2e',0.2,0,0.6),
 nail=mat('nail','#e9d6ff',0.4))
V_=Vector
BC=V_((0,-0.02,1.80))  # brain center
BR=V_((0.56,0.52,0.50))
# ---------------- body
torso = meta([
 ell((0,0.02,0.86),(0.40,0.30,0.24)),
 ell((0,-0.04,1.08),(0.36,0.28,0.26)),
 ell((0,0.02,1.36),(0.56,0.34,0.30)),
 ell((0,0.08,1.62),(0.52,0.30,0.20)),           # traps
 ell((0.20,-0.18,1.42),(0.23,0.15,0.17),rot=(0,0,-8)), ell((-0.20,-0.18,1.42),(0.23,0.15,0.17),rot=(0,0,8)),  # pecs
]+[ell((sx*0.085,-0.25+0.02*(k==0),zz),(0.075,0.05,0.055)) for sx in (1,-1) for k,zz in enumerate((1.20,1.08,0.96))]  # abs
 +[ell((sx*0.40,0.05,1.50),(0.18,0.20,0.22)) for sx in (1,-1)], res=0.02)
parts=[torso]
for s in (1,-1):
    parts.append(meta([
      ball((0.62*s,0.0,1.55),0.24),                                 # delt
      cap((0.64*s,0,1.50),(0.86*s,-0.02,1.14),0.16),
      ell((0.73*s,-0.12,1.33),(0.16,0.14,0.18),rot=(0,-30*s,0)),    # biceps
      ell((0.78*s,0.10,1.32),(0.14,0.13,0.17),rot=(0,-30*s,0)),     # triceps
      cap((0.86*s,-0.02,1.14),(0.98*s,-0.08,0.82),0.14),
      ell((0.90*s,-0.04,1.04),(0.18,0.17,0.19),rot=(0,-20*s,0)),    # forearm bulk
      ell((1.02*s,-0.10,0.66),(0.20,0.19,0.18)),                    # fist
      ball((0.95*s,-0.25,0.72),0.08),
    ]+[ball(((1.0+0.06*kk)*s,-0.27,0.60-0.025*kk),0.065) for kk in range(-1,3)],res=0.02))
    parts.append(meta([cap((0.24*s,0,0.84),(0.30*s,-0.04,0.46),0.20), ell((0.27*s,-0.10,0.66),(0.17,0.15,0.2)),
      cap((0.30*s,-0.04,0.46),(0.32*s,0,0.16),0.15), ell((0.31*s,0.08,0.36),(0.13,0.13,0.17)),
      ell((0.33*s,-0.10,0.07),(0.16,0.22,0.08))]+[ball(((0.33+0.065*kk)*s,-0.31,0.05),0.05) for kk in (-1,0,1)],res=0.02))
body=join(parts,'Body'); remesh(body,0.018,smooth=5); decimate(body,0.5)
set_mat(body,M['skin']); shade_smooth(body)
# darker purple in lower body/back for depth
paint_faces(body,M['skind'],lambda c,n: n.z<-0.55)
# ---------------- brain
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6,radius=1.0,location=(0,0,0)); brain=bpy.context.view_layer.objects.active; brain.name='Brain'
me=brain.data
col=me.color_attributes.new('Col','FLOAT_COLOR','POINT')
pink=V_(hex2lin('#ff7cc8')); groovec=V_(hex2lin('#a3195f')); facec=V_(hex2lin('#d23d9c'))
def sstep(a,b,x):
    t=max(0,min(1,(x-a)/(b-a))); return t*t*(3-2*t)
facew={}
for v in me.vertices:
    p=v.co.copy()
    # face mask: lower front of the brain is smooth skin
    fm=sstep(-0.35,-0.75,p.y)*sstep(0.30,-0.05,p.z)
    q=p*2.6+noise.noise_vector(p*1.7)*0.55
    d,_=noise.voronoi(q)
    f=d[1]-d[0]
    groove=1-sstep(0.0,0.16,f)
    fiss=math.exp(-(p.x/0.045)**2)*sstep(-0.1,0.25,p.z)*(1-fm)
    g=max(groove*(1-fm),fiss)
    disp=(-0.07*groove+0.02)*(1-fm)-0.10*fiss
    np_=p.normalized()
    v.co=V_((np_.x*BR.x,np_.y*BR.y,np_.z*BR.z))+np_*disp*0.55
    c=pink.lerp(groovec,g) if fm<0.5 else facec.lerp(pink,max(0,1-fm*2))
    if fm>=0.5: c=facec
    col.data[v.index].color=(*c,1)
    facew[v.index]=fm
brain.location=BC; activate(brain); bpy.ops.object.transform_apply(location=True)
# brow ridge (angry) + cheek bulges merged into brain via shells is complex -> add brow meshes
set_mat(brain,M['brain']); shade_smooth(brain)
_nt=M['brain'].node_tree; _ca=_nt.nodes.new('ShaderNodeVertexColor'); _ca.layer_name='Col'
_nt.links.new(_ca.outputs['Color'],_nt.nodes['Principled BSDF'].inputs['Base Color'])
for p in brain.data.polygons:
    if all(facew[i]>0.5 for i in p.vertices): pass
add_mat(brain,M['face'])
fi=[x.name for x in brain.data.materials].index('face')
for p in brain.data.polygons:
    if sum(facew[i] for i in p.vertices)/len(p.vertices)>0.5: p.material_index=fi
# mouth cut
MW,MZ,MD=0.34,1.62,0.20
def mouth_outline(n=40):
    up=[];lo=[]
    for i in range(n+1):
        t=-1+2*i/n; x=MW*t
        up.append((x,MZ+0.10*t*t-0.015*(1-t*t)))
        lo.append((x,MZ+0.10*t*t-MD*(1-t*t)**0.7-0.004))
    return up+lo[::-1]
cut=poly_extrude(mouth_outline(),1.0,'XZ','mcut'); cut.location.y=-0.62; activate(cut); bpy.ops.object.transform_apply(location=True)
set_mat(cut,M['mouth']); boolean(brain,cut); shade_smooth(brain)
decimate(brain,0.4)
teeth=[]
for row in ('up','lo'):
    n=10 if row=='up' else 9
    for i in range(n):
        t=-0.9+1.8*i/(n-1); x=MW*t
        zu=MZ+0.10*t*t-0.015*(1-t*t); zl=MZ+0.10*t*t-MD*(1-t*t)**0.7
        z0=zu+0.012 if row=='up' else zl-0.012
        loc,nr=ray_surface(brain,(x,-3,z0),(0,1,0))
        if loc is None: continue
        big = (i in (1,n-2)) and row=='up'
        h=(0.13 if big else 0.085)*(1-0.35*abs(t)); r=0.035 if not big else 0.04
        c=prim('cone',seg=8,r1=r,r2=0.003,depth=h)
        c.location=(loc.x,loc.y+0.03,(zu-h/2+0.015) if row=='up' else (zl+h/2-0.015))
        if row=='up': c.rotation_euler=(math.pi,0,0)
        c.rotation_euler.z=math.atan2(nr.x,-nr.y)*0.6
        activate(c); bpy.ops.object.transform_apply(location=True,rotation=True); set_mat(c,M['teeth']); teeth.append(c)
teeth=join(teeth,'Teeth'); shade_smooth(teeth)
# eyes
eyes=[]
for s in (1,-1):
    ex,ez=0.17*s,1.84
    loc,nr=ray_surface(brain,(ex,-3,ez),(0,1,0))
    e=prim('sphere',seg=24,rings=12); e.scale=(0.11,0.07,0.085); e.rotation_euler=(0,rad(18*s),0)
    activate(e); bpy.ops.object.transform_apply(rotation=True,scale=True)
    e.location=loc+V_((0,0.035,0)); activate(e); bpy.ops.object.transform_apply(location=True); set_mat(e,M['eye'])
    ir=prim('sphere',seg=16,rings=8); ir.scale=(0.05,0.03,0.05); ir.location=loc+V_((-0.02*s,-0.025,-0.005)); activate(ir); bpy.ops.object.transform_apply(location=True,scale=True); set_mat(ir,M['iris'])
    pu=prim('sphere',seg=12,rings=6); pu.scale=(0.026,0.02,0.026); pu.location=loc+V_((-0.022*s,-0.045,-0.005)); activate(pu); bpy.ops.object.transform_apply(location=True,scale=True); set_mat(pu,M['pupil'])
    hl=prim('sphere',seg=8,rings=4); hl.scale=(0.011,0.008,0.011); hl.location=loc+V_((-0.035*s,-0.058,0.012)); activate(hl); bpy.ops.object.transform_apply(location=True,scale=True); set_mat(hl,M['eye'])
    # angry brow: thick bar slanted down toward center
    br=meta([cap((0.05*s,-0.0,0.0),(0.26*s,0,0.07),0.05)],res=0.01); 
    br.location=(0,loc.y-0.0,ez+0.07); activate(br); bpy.ops.object.transform_apply(location=True)
    # push brow onto surface
    bl,bn=ray_surface(brain,(0.15*s,-3,ez+0.09),(0,1,0)); br.location=(0,bl.y+0.02,0); activate(br); bpy.ops.object.transform_apply(location=True)
    set_mat(br,M['face']); shade_smooth(br)
    eyes+= [e,ir,pu,hl,br]
eyes=join(eyes,'Eyes'); shade_smooth(eyes)
# ---------------- crown
ring=prim('cyl',seg=32); ring.scale=(0.17,0.17,0.06); bevel(ring,0.01,2); apply_mods(ring)
pts=[]
for k in range(5):
    a=2*math.pi*k/5
    sp=prim('cone',seg=4,r1=0.07,r2=0.0,depth=0.16); sp.scale=(1,0.35,1); sp.location=(math.cos(a)*0.155,math.sin(a)*0.155,0.12)
    sp.rotation_euler=(0,0,a+math.pi/2); activate(sp); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True); pts.append(sp)
    b=prim('sphere',seg=10,rings=6); b.scale=(0.025,0.025,0.025); b.location=(math.cos(a)*0.155,math.sin(a)*0.155,0.21); activate(b); bpy.ops.object.transform_apply(location=True,scale=True); pts.append(b)
crown=join([ring]+pts,'Crown'); set_mat(crown,M['gold'])
gems=[]
for k in range(5):
    a=2*math.pi*k/5+math.pi/5
    g=prim('sphere',seg=10,rings=6); g.scale=(0.022,0.022,0.022); g.location=(math.cos(a)*0.172,math.sin(a)*0.172,0.0); activate(g); bpy.ops.object.transform_apply(location=True,scale=True); gems.append(g)
gems=join(gems,'Gems'); set_mat(gems,M['gem'])
crown=join([crown,gems],'Crown')
top,_=ray_surface(brain,(0.12,0.0,4),(0,0,-1))
crown.rotation_euler=(rad(-8),rad(14),0); crown.location=top+V_((0,0,0.02)); activate(crown); bpy.ops.object.transform_apply(location=True,rotation=True); shade_smooth(crown)
# ---------------- spiked wristbands
bands=[]
for s in (1,-1):
    w0=V_((0.95*s,-0.07,0.86)); w1=V_((0.98*s,-0.08,0.80)); ax=(V_((1.02*s,-0.10,0.66))-V_((0.86*s,-0.02,1.14))).normalized()
    t=prim('torus',R=0.19,r=0.065,seg=28,mseg=10)
    sp=[]
    for k in range(9):
        a=2*math.pi*k/9
        c=prim('cone',seg=8,r1=0.04,r2=0.0,depth=0.12); c.location=(math.cos(a)*0.27,math.sin(a)*0.27,0); c.rotation_euler=(0,math.pi/2,a)
        activate(c); bpy.ops.object.transform_apply(location=True,rotation=True); sp.append(c)
    b=join([t]+sp,'Band'); q=V_((0,0,1)).rotation_difference(ax); b.rotation_mode='QUATERNION'; b.rotation_quaternion=q; b.location=w1
    activate(b); bpy.ops.object.transform_apply(location=True,rotation=True); set_mat(b,M['gold']); shade_smooth(b); bands.append((s,b))
# ---------------- toenails
nails=[]
for s in (1,-1):
    for kk in (-1,0,1):
        n=prim('sphere',seg=10,rings=6); n.scale=(0.03,0.02,0.018); n.location=((0.33+0.065*kk)*s,-0.37,0.07); activate(n); bpy.ops.object.transform_apply(location=True,scale=True); set_mat(n,M['nail']); nails.append((s,n))
# ---------------- slime drips (raycast onto brain / shoulders)
def drip(surface,origin,direction,ln,r,name):
    loc,nr=ray_surface(surface,origin,direction)
    if loc is None: return None
    a=loc+nr*0.01; b=a+V_((0,0,-ln))+nr*0.02
    ob=meta([cap(a,b,r),ball(b,r*1.45),ell(a,(r*2.2,r*2.2,r*1.0))],res=0.012)
    set_mat(ob,M['slime']); shade_smooth(ob); return ob
sl_head=[];sl_body=[]
random.seed(11)
for (x,z,ln) in [(0.42,1.70,0.18),(0.30,1.98,0.12),(-0.40,1.72,0.22),(-0.28,2.02,0.1),(0.48,1.86,0.14),(-0.50,1.90,0.16),(0.05,2.18,0.08)]:
    d=drip(brain,(x*1.0,-3,z),(0,1,0),ln,0.028,'d')
    if d: sl_head.append(d)
for (x,y,ln,bone) in [(0.45,-0.1,0.25,'chest'),(-0.48,-0.05,0.3,'chest'),(0.62,-0.05,0.2,'upper_arm.L'),(-0.62,0.0,0.22,'upper_arm.R'),(0.15,-0.2,0.22,'chest'),(-0.2,-0.22,0.18,'spine')]:
    d=drip(body,(x,y,3),(0,0,-1),ln,0.032,'d')
    if d: sl_body.append((bone,d))
# ---------------- rig
J={'root':V_((0,0,0)),'hips':V_((0,0,0.86)),'spine':V_((0,0,1.10)),'chest':V_((0,0,1.38)),'neck':V_((0,0,1.62)),'head':V_((0,-0.02,1.72)),'head_top':V_((0,-0.02,2.35))}
for s,S in ((1,'L'),(-1,'R')):
    J.update({'shoulder_'+S:V_((0.58*s,0,1.55)),'elbow_'+S:V_((0.86*s,-0.02,1.14)),'wrist_'+S:V_((0.98*s,-0.08,0.80)),'hand_tip_'+S:V_((1.05*s,-0.11,0.50)),
     'hip_'+S:V_((0.24*s,0,0.84)),'knee_'+S:V_((0.30*s,-0.04,0.46)),'ankle_'+S:V_((0.32*s,0,0.16)),'toe_'+S:V_((0.33*s,-0.34,0.05))})
rig=build_rig(J)
skin(body,rig)
# vertex colors on every part (white) so join keeps brain colors
def white(ob):
    if 'Col' not in ob.data.color_attributes:
        c=ob.data.color_attributes.new('Col','FLOAT_COLOR','POINT')
        for d in c.data: d.color=(1,1,1,1)
for o in [body,brain,teeth,eyes,crown]+[b for _,b in bands]+[n for _,n in nails]+sl_head+[d for _,d in sl_body]: white(o)
rigid(brain,'head'); rigid(teeth,'head'); rigid(eyes,'head'); rigid(crown,'head')
for d in sl_head: rigid(d,'head')
for b,d in sl_body: rigid(d,b)
for s,b in bands: rigid(b,'forearm.'+('L' if s>0 else 'R'))
for s,n in nails: rigid(n,'foot.'+('L' if s>0 else 'R'))
acc=[brain,teeth,eyes,crown]+[b for _,b in bands]+[n for _,n in nails]+sl_head+[d for _,d in sl_body]
for a in acc: a.parent=rig
final=join([body]+acc,'Boss')
final.data.color_attributes.active_color=final.data.color_attributes['Col']
print('TRIS',tri_count(final))
if '--preview' in sys.argv:
    render_preview('/workspace/b3d/prev/boss.png',[final],views=((0,-8,1.3),(5,-6,1.8),(8,0,1.3),(-3,6,1.8)),size=(560,620),target=(0,0,1.2),engine='BLENDER_EEVEE_NEXT')
    sys.exit(0)
import anims; anims.make_all(rig, style='boss', S=1.25)
bpy.context.scene.frame_set(0)
export_glb(OUT,[final,rig])
bpy.ops.wm.save_as_mainfile(filepath='/workspace/b3d/boss.blend')
print('EXPORTED',OUT)
