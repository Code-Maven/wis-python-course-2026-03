import sys
from mycalc import area_of_rectangle

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} WIDTH HEIGHT")
    sys.exit(1)

w = float(sys.argv[1])
h = float(sys.argv[2])

area = area_of_rectangle(w, h)
print(area)

