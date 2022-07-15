from typing import Tuple
import arcpy
from .create_ndvi import create_ndvi;
from .create_veg_raster import create_veg_raster;
from .veg_raster_group import veg_raster_group;
from .veg_raster_cleanup import veg_raster_cleanup;
from .veg_raster_to_poly import veg_raster_to_poly
from .buffer_veg_poly import buffer_veg_poly;

class SpatialLicenseError(Exception): pass

def create_veg_poly(ortho_raster_path: str, veg_poly_out_path: str, veg_poly_buffer_out_path: str, veg_poly_buffer_size: str) -> Tuple[str, str]:
  try:
    # permit using the spatial analyist license from arcgis pro
    if arcpy.CheckExtension('Spatial') == 'Available': arcpy.CheckOutExtension('Spatial')
    else: raise SpatialLicenseError

    print('\n⏳ Generating vegetation polygons')
    
    # create ndvi from orthophotography raster containing NIR and red bands
    ndvi = create_ndvi(ortho_raster_path, 1, 2)
    
    # create a vegetation raster
    veg_raster = create_veg_raster(ndvi)
    veg_raster_grouped = veg_raster_group(veg_raster)
    veg_raster_grouped = veg_raster_cleanup(veg_raster_grouped)

    # create shapefiles
    arcpy.env.overwriteOutput = True
    out = veg_raster_to_poly(veg_raster_grouped, veg_poly_out_path)
    buffer_out = buffer_veg_poly(veg_poly_out_path, veg_poly_buffer_out_path, veg_poly_buffer_size)
    print('✅ DONE')
    return [out, buffer_out]

  except SpatialLicenseError: print('Spatial license in unavailable')
  except arcpy.ExecuteError: print(arcpy.GetMessages(2))

  finally:
    arcpy.CheckInExtension('Spatial')







