import os
import shutil
from typing import List
import arcpy
import veg_poly

class DetectTrees(object):
  def __init__(self):
    self.label = 'Detect Trees from LAS'
    self.description = ''
    self.canRunInBackground = False

  #`
  # Define tool parameters
  # `
  def getParameterInfo(self):

    paramOrthoRaster = arcpy.Parameter(
        displayName='Orthophotography',
        name='ORTHO_RASTER',
        datatype='GPRasterLayer',
        parameterType='Required',
        direction='Input',
      )

    paramVegPoly = arcpy.Parameter(
        displayName='Vegetation Polygon',
        name='VEG_POLY',
        datatype='DEShapefile',
        parameterType='Optional',
        direction='Output',
        category='Intermediate Outputs',
      )

    paramVegPolyBuffered = arcpy.Parameter(
        displayName='Buffered Vegetation Polygon',
        name='VEG_POLY_BUFFERED',
        datatype='DEShapefile',
        parameterType='Optional',
        direction='Output',
        category='Intermediate Outputs',
      )

    paramBuildings = arcpy.Parameter(
        displayName='Buildings',
        name='BUILDINGS',
        datatype='DEShapefile',
        parameterType='Required',
        direction='Input'
      )

    paramBuildingsBuffered = arcpy.Parameter(
        displayName='Buffered Buildings',
        name='BUILDINGS_BUFFERED',
        datatype='DEShapefile',
        parameterType='Optional',
        direction='Output',
        category='Intermediate Outputs'
      )

    paramLAS = arcpy.Parameter(
        displayName='LAS Dataset',
        name='LAS_DATASET',
        datatype='DELasDataset',
        parameterType='Required',
        direction='Input'
      )

    paramFilteredLasDataset = arcpy.Parameter(
        displayName='Filtered LAS dataset',
        name='FILTERED_LAS_DATASET',
        datatype='DELasDataset',
        parameterType='Optional',
        direction='Output',
        category='Intermediate Outputs',
      )

    paramDsm = arcpy.Parameter(
        displayName='Digital Surface Model',
        name='DSM',
        datatype='GPRasterLayer',
        parameterType='Optional',
        direction='Output',
        category='Intermediate Outputs',
      )

    paramTreePoints = arcpy.Parameter(
        displayName='Tree Points',
        name='TREE_POINTS',
        datatype='DEShapefile',
        parameterType='Required',
        direction='Output',
      )

    paramTreeCrownPolygons = arcpy.Parameter(
        displayName='Tree Crown Polygons',
        name='TREE_CROWN_POLYGONS',
        datatype='DEShapefile',
        parameterType='Optional',
        direction='Output',
        category='Intermediate Outputs',
      )

    paramExtent = arcpy.Parameter(
        displayName='Processing extent shapefile',
        name='EXTENT_SHAPE',
        datatype='DEShapefile',
        parameterType='Required',
        direction='Input'
      )

    paramDsmCellSize = arcpy.Parameter(
        displayName='DSM Cell Size',
        name='DSM_CELLSIZE',
        datatype='Long',
        parameterType='Required',
        direction='Input',
      )
    paramDsmCellSize.value = 2

    paramMinTreeHeight = arcpy.Parameter(
        displayName='Minimum Tree Height',
        name='MIN_TREE_HEIGHT',
        datatype='Long',
        parameterType='Required',
        direction='Input',
      )
    paramMinTreeHeight.value = 2

    paramMinTreeCrownHeight = arcpy.Parameter(
        displayName='Minimum Tree Crown Height',
        name='MIN_TREE_CROWN_HEIGHT',
        datatype='Long',
        parameterType='Required',
        direction='Input',
      )
    paramMinTreeCrownHeight.value = 2

    paramWindowFunction = arcpy.Parameter(
        displayName='Window Function',
        name='WINDOW_FUNCTION',
        datatype='GPString',
        parameterType='Required',
        direction='Input',
      )
    paramWindowFunction.value = '0.00901*x + 2.51513'

    paramBufferSize = arcpy.Parameter(
        displayName='Buffer Size',
        name='BUFFER_SIZE',
        datatype='GPLinearUnit',
        parameterType='Required',
        direction='Input',
      )
    paramBufferSize.value = '1 meter'
      
    parameters = [
      paramOrthoRaster,
      paramLAS,
      paramBuildings,
      paramExtent,
      paramBufferSize,
      paramDsmCellSize,
      paramMinTreeHeight,
      paramMinTreeCrownHeight,
      paramWindowFunction,
      paramTreePoints,
      paramDsm,
      paramVegPoly,
      paramVegPolyBuffered,
      paramBuildingsBuffered,
      paramFilteredLasDataset,
      paramTreeCrownPolygons,
    ]
        
    return parameters

  #`
  # Whether this tool is licensed to run. We check the required
  # ArcGIS Pro licenses.
  # `
  def isLicensed(self):
    try:
      if arcpy.CheckExtension('Spatial') != 'Available': raise Exception
    except Exception: return False  # The tool cannot be run
    return True  # The tool can be run

  #`
  # Modify the values and properties of parameters before internal
  # validation is performed. This method is called whenever a parameter
  # has been changed.
  # `
  def updateParameters(self, parameters: List[arcpy.Parameter]):
    return

  #`
  # Modify the messages created by internal validation for each tool
  # parameter. This method is called after internal validation.
  # `
  def updateMessages(self, parameters):
    return

  def execute(self, parameters: List[arcpy.Parameter], messages):
    # import the custom toolbox containing the R scripts
    arcpy.ImportToolbox(f'{arcpy.env.packageWorkspace}/../R/RTools', 'rtools')

    # create a dictionary containing key-value pairs of the parameters
    # where the key is the param name and the value is the text value
    params = {}
    for elem in parameters:
      if (elem.altered):
        params[elem.name] = elem.valueAsText

    # create temporary folders
    TEMP_PATH = f'{arcpy.env.scratchFolder}/DetectTrees'
    if os.path.exists(TEMP_PATH): shutil.rmtree(TEMP_PATH)
    os.mkdir(TEMP_PATH)
    VEG_FOLDER = f'{TEMP_PATH}/veg'
    TILED_LAS_FOLDER = f'{TEMP_PATH}/tiled_las'
    CLIPPED_LAS_FOLDER = f'{TEMP_PATH}/clipped_las'
    FILTERED_LAS_FOLDER = f'{TEMP_PATH}/filtered_las'
    CLIPPED_BUILDINGS_FOLDER = f'{TEMP_PATH}/clipped_buildings'
    os.mkdir(VEG_FOLDER)
    os.mkdir(TILED_LAS_FOLDER)
    os.mkdir(CLIPPED_LAS_FOLDER)
    os.mkdir(FILTERED_LAS_FOLDER)
    os.mkdir(CLIPPED_BUILDINGS_FOLDER)

    # create vegetation polygons based on orthophotography with NIR and red bands
    # so we can target the areas with vegetation
    ORTHO_RASTER = params.get('ORTHO_RASTER')
    VEG_POLY = params.get('VEG_POLY', f'{VEG_FOLDER}/veg_poly')
    VEG_POLY_BUFFERED = params.get('VEG_POLY_BUFFERED', f'{VEG_FOLDER}/veg_poly_buffered')
    EXTENT_SHAPE = params.get('EXTENT_SHAPE')
    CLIPPED_ORTHO_RASTER = params.get('CLIPPED_ORTHO_RASTER', f'{TEMP_PATH}/ortho.tif')
    BUFFER_SIZE = params.get('BUFFER_SIZE')
    arcpy.AddMessage('Clipping orthophoto raster to extent...')
    arcpy.management.Clip(ORTHO_RASTER, None, CLIPPED_ORTHO_RASTER, EXTENT_SHAPE, '256', 'ClippingGeometry', 'MAINTAIN_EXTENT') # clip to input extent to reduce processing time
    arcpy.AddMessage('Generating vegetation raster...')
    veg_poly.create(CLIPPED_ORTHO_RASTER, VEG_POLY, VEG_POLY_BUFFERED, BUFFER_SIZE)

    # clip the input LAS dataset to the provided extent
    # and convert it to non-overlapping square kilometer LAS tiles
    LAS_DATASET = params.get('LAS_DATASET')
    LAS_TILED_DATSET = f'{TILED_LAS_FOLDER}/tiles.lasd'
    LAS_CLIPPED_DATSET = f'{TEMP_PATH}/clipped_las/tiles.lasd'
    arcpy.AddMessage('Clapping LAS dataset to extent...')
    arcpy.ddd.ExtractLas(LAS_DATASET, CLIPPED_LAS_FOLDER, 'MAXOF', EXTENT_SHAPE, 'PROCESS_EXTENT', '', 'MAINTAIN_VLR', 'REARRANGE_POINTS', 'NO_COMPUTE_STATS', LAS_CLIPPED_DATSET, 'NO_COMPRESSION')
    arcpy.AddMessage('Tiling clipped LAS dataset...')
    arcpy.ddd.TileLas(LAS_CLIPPED_DATSET, TILED_LAS_FOLDER, 'tile', LAS_TILED_DATSET, 'COMPUTE_STATS', '1.4', None, 'NO_COMPRESSION', 'REARRANGE_POINTS', None, 'ROW_COLUMN', None, '1 kilometer', '1 kilometer', None)

    # loop through the clipped las tiles to generate a list of las files to process
    las_file_names = []
    for fileName in os.listdir(TILED_LAS_FOLDER):
      if (fileName[-4:len(fileName)] == '.las'): las_file_names.append(fileName)
    
    # create lidar without noise from buildings, non-vegetated areas, and planar surfaces
    BUILDINGS = params.get('BUILDINGS')
    BUILDINGS_CRS = arcpy.Describe(BUILDINGS).spatialReference
    BUILDING_ELEV_ATTR = 'TOPELEV'
    BUILDING_ELEV_ADD = 5
    FILTERED_LAS_DATASET = params.get('FILTERED_LAS_DATASET', f'{FILTERED_LAS_FOLDER}/tiles.lasd')
    
    for index, las in enumerate(las_file_names):
      arcpy.AddMessage(f'Filtering {las} ({index + 1}/{len(las_file_names)})...')
      input_las = f'{TILED_LAS_FOLDER}/{las}'

      # create polygon boundary for each tile
      las_tile_boundary = f'{TILED_LAS_FOLDER}/{las[0:-4]}.shp'
      arcpy.AddMessage('...generating tile boundary')
      arcpy.ddd.PointFileInformation(input_las, las_tile_boundary, 'LAS', '', BUILDINGS_CRS, 'NO_RECURSION')
      
      # clip buildings to las tile and then buffer them
      buildings_clipped = f'{CLIPPED_BUILDINGS_FOLDER}/{las[0:-4]}.shp'
      arcpy.AddMessage('...clipping buildings to tile')
      arcpy.analysis.PairwiseClip(BUILDINGS, las_tile_boundary, buildings_clipped);
      buildings_buffered = f'{CLIPPED_BUILDINGS_FOLDER}/{las[0:-4]}_buffered.shp'
      arcpy.AddMessage('...buffering buildings')
      arcpy.Buffer_analysis(buildings_clipped, buildings_buffered, BUFFER_SIZE, 'FULL', 'ROUND', 'NONE')
      
      # clean las tile
      output_las = f'{FILTERED_LAS_FOLDER}/{las}'
      arcpy.AddMessage('...cleaning las tile')
      arcpy.rtools.PruneBuildingsFromLidar(input_las, buildings_buffered, output_las, BUILDING_ELEV_ATTR, BUILDING_ELEV_ADD, True, VEG_POLY_BUFFERED, True)  
    
    output_las_files = []
    for fileName in os.listdir(FILTERED_LAS_FOLDER): output_las_files.append(f'{FILTERED_LAS_FOLDER}/{fileName}')
    arcpy.AddMessage('Creating filtered LAS dataset from filtered tiles...')
    arcpy.management.CreateLasDataset(output_las_files, FILTERED_LAS_DATASET)

    # convert lidar points to a digital surface model (DSM)
    DSM = f'{TEMP_PATH}/dsm.tif'
    DSM_CLIPPED = params.get('DSM', f'{TEMP_PATH}/dsm_clipped.tif')
    DSM_CELLSIZE = params.get('DSM_CELLSIZE')
    arcpy.AddMessage('Converting filtered LAS dataset to digital surface model (DSM)...')
    arcpy.conversion.LasDatasetToRaster(FILTERED_LAS_DATASET, DSM, 'ELEVATION', 'BINNING MAXIMUM NATURAL_NEIGHBOR', 'FLOAT', 'CELLSIZE', DSM_CELLSIZE) 
    arcpy.AddMessage('Clipping DSM to extent...')
    arcpy.management.Clip(DSM, None, DSM_CLIPPED, EXTENT_SHAPE, '256', 'ClippingGeometry', 'NO_MAINTAIN_EXTENT'); # clip to extent to save processing time

    # generate tree points and tree crowns
    # (tree crowns are skipped if no output path is provided)
    TREE_POINTS = params.get('TREE_POINTS')
    TREE_CROWN_POLYGONS = params.get('TREE_CROWN_POLYGONS', None)
    MIN_TREE_HEIGHT = params.get('MIN_TREE_HEIGHT')
    MIN_TREE_CROWN_HEIGHT = params.get('MIN_TREE_CROWN_HEIGHT')
    WINDOW_FUNCTION = params.get('WINDOW_FUNCTION')
    arcpy.AddMessage('Detecting trees...')
    arcpy.rtools.LidarTreeCrownDelineation(DSM_CLIPPED, MIN_TREE_HEIGHT, WINDOW_FUNCTION, TREE_POINTS, MIN_TREE_CROWN_HEIGHT, TREE_CROWN_POLYGONS)

    return

  #`
  # This method takes place after outputs are outputs are processed and
  # added to the display.
  # `
  def postExecute(self, parameters):
    return