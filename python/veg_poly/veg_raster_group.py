import sys
import arcpy

def veg_raster_group(raster: arcpy.Raster) -> arcpy.Raster:
    sys.stdout.write('Grouping matching vegetation raster pixels...')
    raster = arcpy.sa.RegionGroup(raster, 'FOUR', 'WITHIN', True, 0)
    sys.stdout.write(' ✔ Done\n')
    return raster
