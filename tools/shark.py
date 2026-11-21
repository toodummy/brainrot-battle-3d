import sys; sys.path.insert(0,'/workspace/brainrot-battle-3d/tools')
from b3d_common import *
import random
reset(); random.seed(3)
OUT = sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else '/workspace/b3d/shark.glb'
M = dict(skin=mat('skin','#3b4f72',0.55), belly=mat('belly','#f3f1ea',0.6), mouth=mat('mouth','#6a1024',0.8),
 tongue=mat('tongue','#ff6f8f',0.5), teeth=mat('teeth','#ffffff',0.3), glass=mat('glass','#14141c',0.15),
 gold=mat('gold','#ffc22e',0.3,1.0), shoe=mat('shoe','#f6f6fa',0.5), shoep=mat('shoepurple','#7a3fe0',0.5),
 gill=mat('gill','#25324a',0.7))
V_=Vector
# ---------------- body volumes
torso = meta([
 ell((0,0.01,0.76),(0.31,0.26,0.22)),
 ell((0,-0.03,0.98),(0.37,0.31,0.29)),
 ell((0,0.0,1.19),(0.43,0.32,0.25)),
 ell((0,-0.02,1.42),(0.42,0.35,0.26)),
 ell((0,-0.08,1.70),(0.45,0.48,0.40),rot=(-18,0,0)),
 ell((0,-0.46,1.93),(0.24,0.22,0.18),rot=(-32,0,0)),
 ell((0,0.12,1.64),(0.36,0.32,0.34)),
 # pecs
 ell((0.17,-0.20,1.22),(0.17,0.10,0.13)), ell((-0.17,-0.20,1.22),(0.17,0.10,0.13)),
 # tail stem
 cap((0,0.16,0.80),(0,0.46,0.62),0.14), cap((0,0.46,0.62),(0,0.70,0.52),0.08),
], res=0.02)
parts=[torso]
for s in (1,-1):
    parts.append(meta([
      ball((0.44*s,0.0,1.30),0.18), cap((0.46*s,0,1.27),(0.65*s,-0.02,0.99),0.12),
      ell((0.56*s,-0.08,1.14),(0.13,0.12,0.15),rot=(0,-35*s,0)),
      cap((0.65*s,-0.02,0.99),(0.82*s,-0.05,0.73),0.11), ell((0.72*s,-0.05,0.89),(0.13,0.13,0.15),rot=(0,-30*s,0)),
      ell((0.88*s,-0.07,0.62),(0.15,0.14,0.14)), ball((0.82*s,-0.18,0.66),0.065),
      ball((0.93*s,-0.17,0.58),0.05), ball((0.88*s,-0.19,0.55),0.05), ball((0.83*s,-0.19,0.53),0.05),
    ],res=0.018))
    parts.append(meta([cap((0.19*s,0,0.74),(0.22*s,-0.03,0.44),0.17), cap((0.22*s,-0.03,0.44),(0.235*s,0,0.22),0.14)],res=0.02))
body = join(parts,'Body')
remesh(body,0.017,smooth=6)
decimate(body,0.45)
set_mat(body,M['skin'])
# belly / jaw white
def is_belly(c,n):
    if n.y > -0.15: return False
    e=(c.x/0.33)**2+((c.z-1.14)/0.58)**2
    return e<1.0 and c.y<0.05
# ---------------- mouth (open grin)
MW,MZ,MD=0.37,1.70,0.30
def mouth_outline(n=40):
    up=[];lo=[]
    for i in range(n+1):
        t=-1+2*i/n; x=MW*t
        up.append((x,MZ+0.06*t*t))
        lo.append((x,MZ+0.06*t*t-MD*(1-t*t)**0.8-0.004))
    return up+lo[::-1]
mo=mouth_outline()
cut=poly_extrude(mo,1.0,'XZ','mcut'); cut.location.y=-0.55; activate(cut); bpy.ops.object.transform_apply(location=True)
set_mat(cut,M['mouth'])
boolean(body,cut)
shade_smooth(body)
tongue=meta([ell((0,-0.36,1.46),(0.17,0.15,0.07),rot=(-15,0,0)),ell((0.03,-0.48,1.46),(0.10,0.07,0.06))],res=0.012); set_mat(tongue,M['tongue']); shade_smooth(tongue)
# teeth via surface ray casts along rim
teeth=[]
def surf_y(x,z):
    loc,n=ray_surface(body,(x,-3,z),(0,1,0)); return (loc,n)
for row in ('up','lo'):
    n=11
    for i in range(n):
        t=-0.88+1.76*i/(n-1); x=MW*t
        zu=MZ+0.06*t*t; zl=zu-MD*(1-t*t)**0.8
        if row=='lo' and abs(t)>0.75: continue
        z0 = zu+0.012 if row=='up' else zl-0.012
        loc,nr=surf_y(x,z0)
        if loc is None: continue
        h=0.09*(1-0.3*abs(t)); r=0.038
        c=prim('cone',seg=8,r1=r,r2=0.004,depth=h)
        c.location=(loc.x,loc.y+0.025,(zu-h/2+0.012) if row=='up' else (zl+h/2-0.012))
        if row=='up': c.rotation_euler=(math.pi,0,0)
        # face outward along surface normal (yaw)
        c.rotation_euler.z=math.atan2(nr.x,-nr.y)*0.6
        activate(c); bpy.ops.object.transform_apply(location=True,rotation=True)
        set_mat(c,M['teeth']); teeth.append(c)
teeth=join(teeth,'Teeth'); shade_smooth(teeth)
# ---------------- sunglasses (conforming shell)
def lens(u,v,cx):
    du=abs(u-cx); 
    if v<-0.09 or v>0.07: return False
    w=0.16-0.05*max(0,-v)/0.09   # tapered bottom
    return du<w
def glasses_in(u,v):
    if lens(u,v,0.185) or lens(u,v,-0.185): return True
    return abs(u)<0.04 and 0.03<v<0.065
Dg=V_((0,1,-0.12)).normalized()
gl=shell(body,(0,-0.3,1.86),(1,0,0),V_((0,0.12,1)).normalized(),Dg,glasses_in,(-0.38,0.38),(-0.10,0.08),0.006,0.014,0.04,M['glass'],'Glasses')
# temple arms (go back along sides)
for s in (1,-1):
    loc,nr=ray_surface(body,(s*1.0,-0.30,1.87),(-s,0,0))
    if loc:
        t=prim('cube'); t.scale=(0.014,0.2,0.016); t.location=(loc.x+s*0.012,loc.y+0.12,loc.z+0.01); t.rotation_euler=(rad(-6),0,0)
        activate(t); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True); set_mat(t,M['glass']); gl=join([gl,t],'Glasses')
# ---------------- gills
gills=[]
for s in (1,-1):
    for k in range(3):
        z=1.45; y=-0.02+0.075*k
        loc,nr=ray_surface(body,(s*1.0,y,z),(-s,0,0))
        if loc is None: continue
        g=prim('sphere',seg=12,rings=6); g.scale=(0.012,0.012,0.075)
        g.location=loc; g.rotation_euler=(rad(-12),0,0); activate(g); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        set_mat(g,M['gill']); gills.append(g)
gills=join(gills,'Gills')
# ---------------- fins
def fin(profile,thick,loc,rot,name):
    f=poly_extrude(profile,thick,'YZ',name); bevel(f,thick*0.45,3); subsurf(f,1); apply_mods(f)
    f.location=loc; f.rotation_euler=[rad(a) for a in rot]; activate(f); bpy.ops.object.transform_apply(location=True,rotation=True); set_mat(f,M['skin']); shade_smooth(f); return f
dorsal=fin([(0,0),(0.40,0),(0.42,0.07),(0.36,0.24),(0.32,0.40),(0.37,0.50),(0.22,0.36),(0.10,0.16)],0.08,(0,0.12,1.55),(-10,0,0),'Dorsal')
tailfin=fin([(0,0.0),(0.10,0.08),(0.30,0.36),(0.25,0.38),(0.08,0.14),(0.0,0.06),(0.10,-0.06),(0.24,-0.24),(0.20,-0.25),(0.06,-0.06)],0.065,(0,0.64,0.52),(-15,0,0),'TailFin')
armfins=[]
for s in (1,-1):
    f=fin([(0,0),(0.26,0),(0.32,0.20),(0.19,0.10),(0.04,0.07)],0.05,(0,0,0),(0,0,0),'ArmFin')
    # place on back of forearm, sweeping back
    f.rotation_euler=(rad(-55),0,rad(-30*s)); f.location=(0.74*s,0.06,0.92); activate(f); bpy.ops.object.transform_apply(location=True,rotation=True)
    armfins.append((s,f))
# ---------------- gold chain + medallion
links=[]; N=34
pts=[]
for i in range(N):
    a=-math.pi/2+(i/(N-1)-0.5)*rad(150)
    sa=math.sin(a)
    dip=max(0,-sa)**3
    z=1.40-0.24*dip
    d=V_((math.cos(a),sa,0))
    loc,nr=ray_surface(body,(d.x*1.5,d.y*1.5,z),(-d.x,-d.y,0))
    if loc is None: continue
    pts.append((loc+nr*0.022,nr))
for i,(p,nr) in enumerate(pts):
    q=pts[i+1][0] if i+1<len(pts) else p+(p-pts[i-1][0]); t=(q-p)
    l=prim('torus',R=0.026,r=0.011,seg=12,mseg=6)
    rot=V_((1,0,0)).rotation_difference(t.normalized())
    l.rotation_mode='QUATERNION'; l.rotation_quaternion=rot@Quaternion((1,0,0),math.pi/2*(i%2))
    l.location=p; activate(l); bpy.ops.object.transform_apply(location=True,rotation=True); set_mat(l,M['gold']); links.append(l)
front=min(pts,key=lambda pn:pn[0].y)[0]
med=prim('cyl',seg=24); med.scale=(0.085,0.085,0.016); med.rotation_euler=(rad(80),0,0); bevel(med,0.008,2); apply_mods(med)
rim=prim('torus',R=0.075,r=0.012,seg=24,mseg=6); rim.rotation_euler=(rad(80),0,0); activate(rim); bpy.ops.object.transform_apply(rotation=True)
star=poly_extrude([(0.05*math.cos(math.pi/2+k*math.pi/5)*(1 if k%2==0 else 0.45),0.05*math.sin(math.pi/2+k*math.pi/5)*(1 if k%2==0 else 0.45)) for k in range(10)],0.02,'XZ','star')
medal=join([med,rim,star],'Medal'); medal.location=front+V_((0,-0.035,-0.10)); activate(medal); bpy.ops.object.transform_apply(location=True); set_mat(medal,M['gold'])
chain=join(links+[medal],'Chain'); shade_smooth(chain)
# ---------------- sneakers
shoes=[]
for s in (1,-1):
    x=0.235*s
    up=meta([ell((x,-0.12,0.11),(0.14,0.19,0.095)),ell((x,0.07,0.12),(0.135,0.13,0.11)),ell((x,-0.01,0.25),(0.13,0.13,0.13))],res=0.012)
    remesh(up,0.012,smooth=3); set_mat(up,M['shoe'])
    paint_faces(up,M['shoep'],lambda c,n:(c.y<-0.25 and c.z>0.06) or c.z>0.34 or (c.y>0.14 and c.z>0.08))
    sole=prim('cube'); sole.scale=(0.15,0.27,0.04); sole.location=(x,-0.05,0.04); bevel(sole,0.035,4); apply_mods(sole); set_mat(sole,M['shoe'])
    stripe=prim('cube'); stripe.scale=(0.155,0.275,0.01); stripe.location=(x,-0.05,0.07); bevel(stripe,0.01,2); apply_mods(stripe); set_mat(stripe,M['shoep'])
    laces=[]
    for k in range(3):
        L=prim('cube'); L.scale=(0.07,0.012,0.01); L.location=(x,-0.08-0.05*k,0.25-0.04*k); L.rotation_euler=(rad(-50),0,0)
        activate(L); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True); set_mat(L,M['shoe']); laces.append(L)
    sh=join([up,sole,stripe]+laces,'Shoe'); shade_smooth(sh); shoes.append((s,sh))
# ---------------- rig
J={'root':V_((0,0,0)),'hips':V_((0,0,0.78)),'spine':V_((0,0,0.98)),'chest':V_((0,0,1.20)),'neck':V_((0,-0.02,1.40)),'head':V_((0,-0.05,1.55)),'head_top':V_((0,-0.12,2.15))}
for s,S in ((1,'L'),(-1,'R')):
    J.update({'shoulder_'+S:V_((0.42*s,0,1.29)),'elbow_'+S:V_((0.65*s,-0.02,0.99)),'wrist_'+S:V_((0.82*s,-0.05,0.73)),'hand_tip_'+S:V_((0.93*s,-0.08,0.53)),
     'hip_'+S:V_((0.19*s,0,0.74)),'knee_'+S:V_((0.22*s,-0.03,0.44)),'ankle_'+S:V_((0.235*s,0,0.2)),'toe_'+S:V_((0.235*s,-0.30,0.06))})
rig=build_rig(J,extra=[('tail1',(0,0.16,0.80),(0,0.46,0.62),'hips',False),('tail2',(0,0.46,0.62),(0,0.85,0.48),'tail1',True)])
skin(body,rig)
def belly_in(u,v):
    if (u/0.33)**2+((v-1.06)/0.42)**2>=1: return False
    t=max(-1,min(1,u/MW)); lip=MZ+0.06*t*t-MD*(1-t*t)**0.8-0.025
    return v<lip
belly=shell(body,(0,0,0),(1,0,0),(0,0,1),(0,1,0),belly_in,(-0.36,0.36),(0.6,1.5),0.008,0.003,0.012,M['belly'],'Belly',smooth_iter=1)
transfer_weights(body,belly)
def W(ob,b): rigid(ob,b)
W(tongue,'head'); W(teeth,'head'); W(gl,'head'); W(gills,'neck'); W(dorsal,'chest'); W(tailfin,'tail2'); W(chain,'chest')
for s,f in armfins: W(f,'forearm.'+('L' if s>0 else 'R'))
for s,sh in shoes: W(sh,'foot.'+('L' if s>0 else 'R'))
acc=[belly,tongue,teeth,gl,gills,dorsal,tailfin,chain]+[f for _,f in armfins]+[sh for _,sh in shoes]
for a in acc: a.parent=rig
final=join([body]+acc,'Shark')
print('TRIS',tri_count(final))
if '--preview' in sys.argv:
    render_preview('/workspace/b3d/prev/shark.png',[final],views=((0,-7,1.2),(4.5,-5.5,1.6),(7,0,1.2),(-3,5,1.5)),size=(500,620),target=(0,0,1.05))
    sys.exit(0)
import anims; anims.make_all(rig, style='shark')
bpy.context.scene.frame_set(0)
export_glb(OUT,[final,rig])
bpy.ops.wm.save_as_mainfile(filepath='/workspace/b3d/shark.blend')
print('EXPORTED',OUT)
