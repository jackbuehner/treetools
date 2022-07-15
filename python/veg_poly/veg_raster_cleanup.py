import sys
import arcpy

def veg_raster_cleanup(raster: arcpy.Raster) -> arcpy.Raster:
    sys.stdout.write('Removing non-vegetation pixels and isolated vegetation pixels...')
    new_raster = arcpy.sa.ExtractByAttributes(raster, 'Count > 3 And LINK = 1')
    sys.stdout.write(' ✔ Done \n')
    return new_raster
