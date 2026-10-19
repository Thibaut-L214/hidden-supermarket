"""Schematic indoor cattle finishing chain, elevated observation only.

Blender +Y faces forward (glTF -Z). Ground -12m, terrace 0m. Distances
are compressed. Opaque killing building never reveals its interior.
Run: Blender -b --factory-startup -P this.py -- blender/terrace_beef.blend
"""
import math
import os
import random
import sys
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from common import MeshBuilder, box, empty, helper_volume, material, bevel, reset_scene, save_blend
import terrace_props as props

G = -12
M = {}

def mats():
    colors = {'concrete':'#C8C6BB','ground':'#929B80','road':'#797D79','steel':'#929C9F',
              'wall':'#B8AD96','roof':'#787F7D','straw':'#C8AC66','feed':'#A19464',
              'water':'#6E9396','hide':'#BA9873','hide2':'#8D6952','muzzle':'#6B5A50',
              'hoof':'#423F3A','eye':'#282924','tag':'#E0BC50','white':'#E5E5D9',
              'plant':'#BDCBCB','cold':'#D9E5E3','carton':'#BEA784','blue':'#78969B'}
    for k,c in colors.items(): M[k]=material('M_BEEF_'+k.upper(),c,metallic=.45 if k=='steel' else 0)
    props.materials()

def rails(name, a, b, parent, z=G, height=1.5):
    x0,y0=a; x1,y1=b
    length=math.hypot(x1-x0,y1-y0)
    m=MeshBuilder()
    for i in range(max(1,math.ceil(length/2))+1):
        f=i/max(1,math.ceil(length/2)); x=x0+(x1-x0)*f; y=y0+(y1-y0)*f
        m.cylinder((x,y,z),.025 if height<1.1 else .045,height,M['steel'],segments=8)
    for h in ((.3,.7,1.02) if height<1.1 else (.45,.95,1.4)):
        r=.018 if height<1.1 else .035
        m.limb((x0,y0,z+h),(x1,y1,z+h),r,r,M['steel'])
    m.build(name,parent=parent)

def animal(name, position, parent, variation=0):
    """Ground-centred independent root, top-jointed legs, facing local +Y."""
    root=empty(name,position,parent)
    root['animalIndex']=variation
    m=MeshBuilder(); hide=M['hide2'] if variation%3==1 else M['hide']
    m.ellipsoid((0,-.1,1.13),(.39,.86,.47),hide,u=14,v=9)
    m.ellipsoid((0,.49,1.25),(.34,.39,.43),hide,u=12,v=8)
    m.ellipsoid((0,.87,1.36),(.22,.38,.28),hide,u=12,v=8)
    m.ellipsoid((0,1.12,1.21),(.23,.17,.14),M['muzzle'])
    # Ears, nostrils and visible identification tags.
    for side in (-1,1):
        m.ellipsoid((side*.29,.82,1.53),(.17,.08,.065),hide)
        m.ellipsoid((side*.205,.96,1.46),(.025,.024,.026),M['eye'])
        m.ellipsoid((side*.10,1.257,1.25),(.035,.012,.02),M['hoof'])
        m.box((side*.29-.035,.77,1.39),(side*.29+.035,.795,1.49),M['tag'])
    m.limb((0,-.83,1.32),(.04,-.97,.55),.035,.017,hide)
    m.ellipsoid((.04,-.97,.48),(.05,.05,.13),M['muzzle'])
    m.build(name+'_BODY',parent=root)
    for j,(x,y) in enumerate(((-.25,-.58),(.25,-.58),(-.25,.48),(.25,.48))):
        leg=empty('CATTLE_LEG_'+name+'_'+str(j),(x,y,1.0),root)
        limb=MeshBuilder()
        limb.limb((0,0,0),(0,-.025,-.48),.09,.055,hide)
        limb.limb((0,-.025,-.48),(0,.015,-.91),.055,.035,hide)
        limb.box((-.065,-.065,-1),(.065,.11,-.88),M['hoof'])
        limb.build(name+'_LIMB_'+str(j),parent=leg)
    return root

def cattle_group(name, positions, parent):
    group=empty(name,parent=parent)
    for i,p in enumerate(positions): animal(name+'_'+str(i+1).zfill(2),p,group,i)
    return group

def terrain(root):
    box('TERRAIN_BEEF',(-90,-12,G-.4),(90,110,G),M['ground'],root)
    box('ROAD_BEEF',(-5,10,G+.01),(11,75,G+.06),M['road'],root)
    box('ROAD_BEEF_LOADING',(-12,2,G+.01),(-5.05,19,G+.068),M['road'],root)
    box('ROAD_BEEF_FARM',(-13,13,G+.01),(11,19,G+.062),M['road'],root)
    box('ROAD_BEEF_ABATTOIR',(4,25,G+.01),(19,33,G+.064),M['road'],root)
    box('ROAD_BEEF_DELIVERY',(8,12,G+.01),(42,18,G+.066),M['road'],root)
    # Observation deck fully enclosed except the threshold against the store.
    box('TERRACE_BEEF_FLOOR',(-6,0,-.3),(6,7,0),M['concrete'],root)
    box('TERRACE_BEEF_PLINTH',(-6,-.3,G),(6,7,-.3),M['concrete'],root)
    for label,a,b in [('N',(-6,6.9),(6,6.9)),('W',(-5.9,0),(-5.9,7)),('E',(5.9,0),(5.9,7))]:
        rails('TERRACE_BEEF_RAIL_'+label,a,b,root,z=0,height=1.05)
        x0,y0=a;x1,y1=b
        helper_volume(box('COL_RAIL_BEEF_'+label,(min(x0,x1)-.05,min(y0,y1)-.05,0),(max(x0,x1)+.05,max(y0,y1)+.05,1.05),None,root))
    # Solid rear guards around the 3m portal prevent leaving the observation area.
    for label,x0,x1 in [('L',-6,-1.5),('R',1.5,6)]:
        box('TERRACE_BEEF_BACK_'+label,(x0,-.15,0),(x1,0,2.3),M['concrete'],root)
        helper_volume(box('COL_BEEF_BACK_'+label,(x0,-.15,0),(x1,0,2.3),None,root))
    empty('ANCHOR_BEEF_VIEW',(0,6.2,1.6),root)
    empty('ANCHOR_BEEF_FOCUS',(-2,28,G+1),root)
    # Sparse tree belt establishes site boundaries without obscuring buildings.
    rng=random.Random(43)
    trees=MeshBuilder()
    for i in range(25):
        x=-38+i*3.3;y=63+rng.uniform(-3,3)
        trees.cylinder((x,y,G),.15,3,M['hide2'])
        trees.ellipsoid((x,y,G+3.2),(1.5,1.6,2.3),M['ground'])
    trees.build('LANDSCAPE_BEEF_TREES',parent=root)

def farm(root,roofs,interior):
    farm=empty('BUILDING_BEEF_FARM',parent=root)
    box('BEEF_FARM_SLAB',(-18,19,G-.1),(-3,34,G+.05),M['concrete'],farm)
    # Low front wall leaves cattle visible after roof reveal; side doorway to loading lane.
    for n,a,b in [('W',(-18,19,G),(-17.8,34,G+3)),('N',(-18,33.8,G),(-3,34,G+3)),('E',(-3.2,23,G),(-3,34,G+3)),('S',(-18,19,G),(-9.5,19.2,G+1))]:
        box('BEEF_FARM_WALL_'+n,a,b,M['wall'],farm)
    roof=MeshBuilder().gable((-18.3,18.7,G+3.1),(-2.7,34.3,G+3.25),1.7,M['roof'])
    roof.build('ROOF_BEEF_FARM',parent=roofs)
    rafters=MeshBuilder()
    for y in (19.3,23,27,30.5,33.5):
        for x in (-17.7,-3.3): rafters.box((x-.07,y-.07,G),(x+.07,y+.07,G+3.2),M['steel'])
        rafters.limb((-17.7,y,G+3.1),(-10.5,y,G+4.6),.065,.065,M['steel'])
        rafters.limb((-10.5,y,G+4.6),(-3.3,y,G+3.1),.065,.065,M['steel'])
    rafters.build('BEEF_FARM_FRAME',parent=roofs)
    box('BEEF_STRAW_BED',(-17.4,22,G+.06),(-7,33.4,G+.12),M['straw'],interior)
    rng=random.Random(22); straw=MeshBuilder()
    for _ in range(220):
        x=rng.uniform(-17.2,-7.2);y=rng.uniform(22.2,33.2)
        straw.limb((x,y,G+.13),(x+rng.uniform(-.18,.18),y+.21,G+.13),.009,.009,M['feed'],segments=4)
    straw.build('BEEF_STRAW_DETAIL',parent=interior)
    rails('BEEF_FEED_BARRIER',(-6.7,23),(-6.7,33),interior)
    box('BEEF_FEED_TROUGH',(-6.4,23,G+.04),(-5.4,33,G+.25),M['feed'],interior)
    box('BEEF_WATER_TROUGH',(-17.1,20,G+.05),(-14.5,21,G+.55),M['steel'],interior)
    box('BEEF_DRINKING_WATER',(-17,20.1,G+.5),(-14.6,20.9,G+.52),M['water'],interior)
    # Side and collecting lane rails, leaving a real loading exit at y=19.
    rails('BEEF_LANE_LEFT',(-9.4,19),(-9.4,22),interior)
    rails('BEEF_LANE_RIGHT',(-6.6,19),(-6.6,22),interior)
    animals=empty('ANIMALS_BEEF',parent=interior)
    cattle_group('CATTLE_BEEF_FARM',[(x,y,G+.13) for y in (24.5,27.6,30.7) for x in (-14.5,-10.6)],animals)
    # Non-timeline cattle document feeding and resting areas.
    feeding=animal('BEEF_FEEDING_CATTLE',(-7.5,31,G+.13),animals,7)
    feeding.rotation_euler.z=-math.pi/2
    # Non-timeline resting individuals document a resting area.
    resting=empty('BEEF_RESTING_CATTLE',parent=animals)
    for i,(x,y) in enumerate(((-16,23),(-16,28))):
        m=MeshBuilder();m.ellipsoid((x,y,G+.5),(.45,.8,.4),M['hide'])
        m.ellipsoid((x,y+.8,G+.95),(.22,.3,.25),M['hide'])
        m.ellipsoid((x,y+1,G+.86),(.22,.15,.12),M['muzzle'])
        for side in (-1,1): m.ellipsoid((x+side*.27,y+.73,G+1.1),(.16,.06,.05),M['hide'])
        m.build('BEEF_RESTING_'+str(i),parent=resting)

def ramp(name,x,y0,y1,root):
    """Rear ramp from ground at y0 to 0.9m truck deck at y1."""
    m=MeshBuilder()
    # Closed wedge, with a non-slip top and rails following the slope.
    m.quad(((x-1.1,y0,G+.03),(x+1.1,y0,G+.03),(x+1.1,y1,G+.9),(x-1.1,y1,G+.9)),M['steel'])
    for side in (-1,1):
        xx=x+side*1.08
        m.limb((xx,y0,G+1),(xx,y1,G+1.9),.04,.04,M['steel'])
        for t in (0,.5,1):
            yy=y0+(y1-y0)*t;zz=G+.9*t
            m.cylinder((xx,yy,zz),.035,1,M['steel'],segments=6)
    for i in range(12):
        f=i/12;yy=y0+(y1-y0)*f;zz=G+.9*f+.04
        m.limb((x-1.05,yy,zz),(x+1.05,yy,zz),.014,.014,M['hoof'],segments=6)
    m.build(name,parent=root)

def truck(name,position,root,refrigerated=False):
    # Reuse detailed cab/wheels; adjust entire body so its deck top sits at 0.9m.
    truck=props.truck(name,name+'_UNUSED_CARGO',lambda m,x,y,z:None,M['blue'] if refrigerated else M['white'],position,root,slats=not refrigerated)
    unused=bpy.data.objects.get(name+'_UNUSED_CARGO')
    if unused:
        for child in list(unused.children): bpy.data.objects.remove(child,do_unlink=True)
        bpy.data.objects.remove(unused,do_unlink=True)
    body=bpy.data.objects[name+'_BODY'];body.location.z=-.4
    if refrigerated:
        m=MeshBuilder()
        m.box((-1.2,-4.3,.9),(1.2,2.1,3.2),M['cold'])
        m.box((-.6,2.11,2.35),(.6,2.45,3.15),M['white'])
        for x in (-.4,-.2,0,.2,.4): m.box((x,2.451,2.48),(x+.07,2.47,3),M['steel'])
        # Rear pair of insulated doors and latches.
        for x in (-1.15,.03):
            m.box((x,-4.34,1),(x+1.1,-4.3,3.12),M['white'])
            m.cylinder((x+.8,-4.37,1.1),.025,1.9,M['steel'],segments=8)
        m.build(name+'_INSULATED_BODY',parent=truck)
    return truck

def plant(root,roofs,interior):
    plant=empty('ABATTOIR_BEEF',parent=root)
    box('BEEF_ABATTOIR_SLAB',(13,30,G-.1),(31,49,G+.03),M['concrete'],plant)
    # Waiting pen roof reveals only pens, never the killing building.
    box('BEEF_WAITING_BACK',(13,42,G),(24,42.2,G+3),M['plant'],plant)
    MeshBuilder().gable((12.8,30,G+3),(24.2,42.4,G+3.2),.7,M['roof']).build('ROOF_BEEF_WAITING',parent=roofs)
    for n,a,b in [('W',(13,30),(13,42)),('E_S',(23,30),(23,31)),('E_N',(23,35),(23,42)),('N',(13,41.5),(23,41.5))]:rails('BEEF_WAITING_RAIL_'+n,a,b,interior)
    rails('BEEF_WAITING_DIVIDER',(13,41),(18,41),interior)
    box('BEEF_WAITING_WATER',(13.3,39,G),(15.3,40,G+.5),M['steel'],interior)
    box('BEEF_WAITING_WATER_SURFACE',(13.4,39.1,G+.48),(15.2,39.9,G+.5),M['water'],interior)
    cattle_group('CATTLE_BEEF_WAITING',[(x,y,G+.05) for y in (33,36,39) for x in (15.6,20.8)],interior)
    # Curved/offset approach corridor enters an opaque building; no machinery or carcasses.
    for n,a,b in [('A',(23.5,35),(23.5,43)),('B',(25.5,35),(25.5,42.7))]: rails('BEEF_APPROACH_RAIL_'+n,a,b,interior)
    opaque=empty('BEEF_KILLING_OPAQUE',parent=plant)
    # Real entry with an offset internal corridor. Roof and baffle screen the interior.
    for suffix,a,b in [
        ('W',(23.2,42.1,G),(23.4,49,G+4)),
        ('E',(30.8,42.1,G),(31,49,G+4)),
        ('N',(23.2,48.8,G),(31,49,G+4)),
        ('FRONT_L',(23.2,42.1,G),(23.5,42.3,G+4)),
        ('FRONT_R',(25.5,42.1,G),(31,42.3,G+4)),
        ('LINTEL',(23.5,42.1,G+2.5),(25.5,42.3,G+4)),
        ('BAFFLE',(23.4,44,G),(25.7,44.2,G+4)),
    ]: box('BEEF_KILLING_ENCLOSURE_'+suffix,a,b,M['plant'],opaque)
    box('BEEF_KILLING_ROOF',(23.1,42,G+4),(31.1,49.1,G+4.2),M['roof'],opaque)
    # Hidden endpoint roots sit beyond the opaque wall. Runtime hides them after entry.
    cattle_group('CATTLE_BEEF_APPROACH',[(27+(i%3)*1.2,45.5+(i//3)*1.6,G+.05) for i in range(6)],interior)
    # Three separate rooms with removable roof omitted: closed sanitary storage boxes only.
    for name,x0,x1,y0,y1,col in [('COLD_ROOM_BEEF',33,41,38,47,'cold'),('CUTTING_BEEF',33,41,28,36,'plant'),('PACKING_BEEF',33,41,19,26,'white')]:
        room=empty(name,parent=root)
        box(name+'_FLOOR',(x0,y0,G),(x1,y1,G+.08),M['concrete'],room)
        for suffix,a,b in [('BACK',(x0,y1-.15,G),(x1,y1,G+2.2)),('SIDE',(x1-.15,y0,G),(x1,y1,G+2.2))]:box(name+'_'+suffix,a,b,M[col],room)
        # Wall panels and stainless work tables.
        for y in range(y0+1,y1-1,2):
            box(name+'_TABLE_'+str(y),(x0+1,y,G+.7),(x0+6,y+.8,G+.8),M['steel'],room)
            for x in (x0+1.1,x0+5.8): box(name+'_LEG_'+str(x)+'_'+str(y),(x,y,G),(x+.06,y+.75,G+.7),M['steel'],room)
    for groupname,origin,carton in [('MEAT_BEEF_CHILLED',(34,40,G+.85),False),('MEAT_BEEF_CUT',(34,30,G+.85),False),('CARTONS_BEEF_PACKED',(34,21,G+.85),True)]:
        cargo=empty(groupname,origin,root)
        for i in range(6):
            x=(i%3)*1.7;y=(i//3)*1.7
            m=MeshBuilder().box((x,y,0),(x+1.2,y+1.1,.5),M['carton'] if carton else M['white'])
            m.box((x+.15,y-.005,.18),(x+.5,y,.36),M['white'] if carton else M['blue'])
            m.build(groupname+'_'+str(i).zfill(2),parent=cargo)


def paths(root):
    points={
      'PATH_BEEF_LOAD':[(-8,23.5,G+.13),(-8,18.8,G+.03),(-11,17.5,G+.03),(-11,2.7,G+.03),(-8,2.7,G+.03),(-8,5.7,G+.9),(-8,6.5,G+.9)],
      'PATH_BEEF_ANIMALS':[(-8,10,G),(-8,12.5,G),(7,12.5,G),(7,22,G),(18,22,G),(18,28,G)],
      'PATH_BEEF_UNLOAD':[(18,23.7,G+.9),(18,20.7,G+.03),(15,25,G+.03),(15,33.5,G+.05),(18,33.5,G+.05)],
      'PATH_BEEF_APPROACH':[(21.5,32,G+.05),(24.5,34,G+.05),(24.5,43.4,G+.05),(26.8,43.4,G+.05),(27,45,G+.05)],
      'PATH_BEEF_DELIVERY':[(37,15,G),(18,15,G),(8,15,G),(8,9,G)],
    }
    for name,coords in points.items():
        for i,p in enumerate(coords): empty(name+'_'+str(i).zfill(2),p,root)

def main():
    reset_scene();mats()
    root=empty('TERRACE_BEEF_ROOT')
    terrain(root)
    roofs=empty('ROOF_BEEF',parent=root);interior=empty('INTERIOR_BEEF',parent=root)
    farm(root,roofs,interior);plant(root,roofs,interior)
    livestock=truck('TRUCK_BEEF_ANIMALS',(-8,10,G),root)
    # Two abreast, three rows, enough head clearance and a correct 0.9m deck.
    cattle_group('CATTLE_BEEF_TRUCK',[(x,y,.9) for y in (-3.35,-1.35,.65) for x in (-.56,.56)],livestock)
    ramp('BEEF_LOADING_RAMP',-8,2.7,5.7,root)
    ramp('BEEF_UNLOADING_RAMP',18,20.7,23.7,root)
    delivery=truck('TRUCK_BEEF_DELIVERY',(37,15,G),root,True)
    cargo=empty('CARGO_BEEF_DELIVERY',parent=delivery)
    for i in range(6):
        x=-1+(i%2)*1.05;y=-4+(i//2)*1.8
        MeshBuilder().box((x,y,.9),(x+.95,y+1.2,1.8),M['carton']).build('BEEF_DELIVERY_CARTON_'+str(i),parent=cargo)
    paths(root)
    # Anchors for documentary panels, all visible from the terrace.
    for name,p in [('FARM',(-10,24,G+3)),('TRANSPORT',(3,21,G+2)),('ABATTOIR',(22,36,G+3)),('COLD_ROOM',(36,42,G+2)),('CUTTING',(36,32,G+2)),('PACKING',(36,23,G+2))]: empty('ANCHOR_BEEF_'+name,p,root)
    argv=sys.argv[sys.argv.index('--')+1:]
    save_blend(os.path.abspath(argv[0]))

if __name__=='__main__': main()
