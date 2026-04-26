#import math
from math import pi, e, sin

#radius = input("Enter the radius of the circle: ")
#print(radius)
#radius = int(radius)
#print(radius)
#area = math.pi * radius ** 2
#print(area)

radius = float(input("Enter the radius of the circle: "))

#area = math.pi * radius ** 2
#circumference = 2 * math.pi * radius
area = pi * radius ** 2
circumference = 2 * pi * radius

print(f"Area: {area}")
print(f"Circumference: {circumference}")
