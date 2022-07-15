import sys
import arcpy

def create_veg_raster(raster: arcpy.Raster) -> arcpy.Raster:
    sys.stdout.write('Creating initital vegetation raster...')
    raster = arcpy.sa.RasterCalculator([raster], ['x'], 'x > 0.1')
    sys.stdout.write(' ✔ Done\n')
    return raster
