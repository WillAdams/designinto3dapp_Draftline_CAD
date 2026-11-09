SAMPLE_PROGRAM = '''# Draftline DSL — dimensions are in millimetres
UNITS mm

# A plane is an origin plus two local drawing axes (u, v).
# LAYER color accepts ACI 1-255 or a basic name; entities inherit unless color= overrides.
LAYER name=frame color=7
LAYER name=divider color=cyan
LAYER name=detail color=green
LAYER name=accent color=magenta

# Each entity's plane, in-plane rotation, normal offset and layer are explicit.
PLANE XY origin=0,0,0 u=1,0,0 v=0,1,0
PLANE TOP origin=0,0,70 u=1,0,0 v=0,-1,0
PLANE FRONT origin=0,0,0 u=1,0,0 v=0,0,1
PLANE RIGHT origin=100,0,0 u=0,1,0 v=0,0,1
PLANE BACK origin=100,60,0 u=-1,0,0 v=0,0,1

# LINE name=... from=x,y to=x,y plane=... rotate=degrees offset=... layer=...
LINE name=top-edge-a from=0,0 to=100,0 plane=TOP rotate=0 offset=0 layer=frame
LINE name=top-edge-b from=100,0 to=100,60 plane=TOP rotate=0 offset=0 layer=frame
LINE name=front-rail from=0,0 to=100,0 plane=FRONT rotate=0 offset=0 layer=frame
LINE name=front-upright from=0,0 to=0,70 plane=FRONT rotate=0 offset=0 layer=frame
LINE name=front-right-upright from=100,0 to=100,70 plane=FRONT rotate=0 offset=0 layer=frame
LINE name=right-rail from=0,0 to=60,0 plane=RIGHT rotate=0 offset=0 layer=frame
LINE name=top-mark from=38,30 to=62,30 plane=TOP rotate=10 offset=1 layer=detail
LINE name=offset-divider from=20,22 to=80,22 plane=FRONT rotate=0 offset=3 layer=divider

# CIRCLE name=... center=x,y radius=... plane=... rotate=... offset=... layer=...
CIRCLE name=badge center=50,44 radius=9 plane=FRONT rotate=0 offset=1 layer=detail
CIRCLE name=raised-fastener center=18,18 radius=3 plane=XY rotate=0 offset=74 layer=detail

# ARC uses counter-clockwise local angles in degrees (end may exceed 360).
# ARC name=... center=x,y radius=... start=... end=... plane=... rotate=... offset=... layer=...
ARC name=badge-sweep center=50,44 radius=13 start=205 end=335 plane=FRONT rotate=8 offset=1 layer=accent color=yellow
ARC name=top-corner center=88,48 radius=8 start=0 end=90 plane=TOP rotate=0 offset=0 layer=detail
'''
