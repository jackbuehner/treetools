import sys
import arcpy

def veg_raster_to_poly(raster: arcpy.Raster, out_path: str) -> str:
    sys.stdout.write('Converting filtered vegetation raster to polygon...')
    arcpy.RasterToPolygon_conversion(raster, out_path, False, 'Value', True)
    sys.stdout.write(' ✔ Done\n')
    return out_path
