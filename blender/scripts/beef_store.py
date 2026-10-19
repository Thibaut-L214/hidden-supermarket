"""Refrigerated scannable beef shelf; geometry stays within the north-wall opening."""
from common import MeshBuilder, empty, box, bevel, helper_volume, material

def beef_shelf(root, M):
    shelf = empty('SHELF_BEEF_ROOT', (6,8.4,0), root)
    shelf['chainId'] = 'beef'
    tray = material('M_BEEF_TRAY', '#E5DECE')
    meat = material('M_BEEF_PACKAGED', '#98594F')
    dark = material('M_BEEF_REFRIGERATOR', '#59686A', metallic=.3)
    for side, label in ((-1,'L'),(1,'R')):
        hinge = empty('HINGE_BEEF_'+label, (side*1.5,0,0), shelf)
        frame, goods = MeshBuilder(), MeshBuilder()
        x0,x1 = (0,1.5) if side < 0 else (-1.5,0)
        frame.box((x0,.55,.1),(x1,.6,2.2),dark)
        frame.box((x0,0,0),(x1,.6,.12),dark)
        frame.box((x0,-.03,2.08),(x1,.6,2.2),dark)
        for x in (x0,x1-.04): frame.box((x,0,.1),(x+.04,.6,2.1),dark)
        for z in (.14,.61,1.08,1.55):
            frame.box((x0,0,z),(x1,.55,z+.025),M['shelf'])
            frame.box((x0,-.015,z-.035),(x1,.015,z+.025),M['rail_label'])
            for i in range(5):
                x = x0+.045+i*.29
                for y in (.07,.32):
                    goods.box((x,y,z+.025),(x+.25,y+.2,z+.055),tray)
                    if side < 0:
                        goods.ellipsoid((x+.125,y+.1,z+.065),(.1,.075,.025),meat)
                    else:
                        # Fine separate ridges distinguish minced beef from a smooth steak.
                        goods.box((x+.025,y+.025,z+.055),(x+.225,y+.175,z+.07),meat)
                        for strand in range(8):
                            sy=y+.03+strand*.018
                            dx=.008 if strand%2 else 0
                            goods.box((x+.03+dx,sy,z+.07),(x+.215-dx,sy+.009,z+.082),meat)
                    goods.box((x+.17,y+.005,z+.08),(x+.23,y+.07,z+.085),M['sign'])
        frame.box((x0+.05,.02,2.04),(x1-.05,.045,2.07),M['shelf_light'])
        door=bevel(frame.build('DOOR_BEEF_'+label,parent=hinge),.006)
        goods.build('DOOR_BEEF_'+label+'_GOODS',parent=door)
        product='STEAK' if side<0 else 'MINCE'
        sign=MeshBuilder().box((-.67,-.015,-.08),(.67,.015,.08),M['sign']).build(
            'PRODUCT_SIGN_BEEF_'+product,((x0+x1)/2,-.04,1.95),door)
        sign['label']='Steaks' if side<0 else 'Viande hachée'
        helper_volume(MeshBuilder().box((x0,0,0),(x1,.6,2.2)).build('COL_DOOR_BEEF_'+label,parent=door))
    helper_volume(box('SCAN_BEEF',(4.5,8.4,0),(7.5,9,2.2),None,shelf))
    helper_volume(box('TRIGGER_BEEF_ENTRY',(4.5,8.4,0),(7.5,9.6,2.2),None,shelf))
    box('STORE_THRESHOLD_BEEF',(4.5,9,-.1),(7.5,9.3,0),M['floor'],shelf)
    empty('ANCHOR_BEEF_TERRACE',(0,.9,0),shelf)
    box('SIGN_BEEF',(5.1,8.96,2.45),(6.9,9,2.95),M['sign'],shelf)
    box('PICTO_SCAN_BEEF',(7,8.96,2.5),(7.4,9,2.9),M['sign'],shelf)
