import sys
import arcpy

def buffer_veg_poly(veg_poly_shp_path: str, out_path: str, size: str) -> str:
    sys.stdout.write('Generating vegetation polygon buffer...')
    arcpy.Buffer_analysis(veg_poly_shp_path, out_path, size, "FULL", "ROUND", "NONE")
    sys.stdout.write(' ✔ Done\n')
    return out_path

