from psycopg2.extensions import adapt, AsIs

class Cube(object):
    def __init__(self, r, g, b):
         self.r = r
         self.g = g
         self.b = b

def adapt_cube(cube):
    return AsIs("'(%s, %s, %s)'" % (adapt(cube.r), adapt(cube.g), adapt(cube.b)))
