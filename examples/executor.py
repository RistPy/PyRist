import ristpy

ristpy.rist('test.rist', flags=ristpy.EXECUTE)
# or
ristpy.execute('test.rist', flags=ristpy.COMPILE|ristpy.FILE)
