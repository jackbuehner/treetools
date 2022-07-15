import sys
import arcpy

def create_ndvi(ortho: str, nir_band: int, red_band: int) -> arcpy.Raster:
  sys.stdout.write('Creating normalized difference vegetation index (NDVI)...')
  ndvi = arcpy.sa.BandArithmetic(ortho, f'{nir_band} {red_band}', 1)
  sys.stdout.write(' ✔ Done\n')
  return ndvi
