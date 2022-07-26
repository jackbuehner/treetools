options(install.packages.check.source = 'no')

options("rgdal_show_exportToProj4_warnings" = "none") # hide proj4 warnings

use_package = function(p) {
  if (!is.element(p, installed.packages()[, 1])) {
    message('Installing package: ', p)
    install.packages(p, repos = 'https://archive.linux.duke.edu/cran/', type = 'both')
  }
  require(p, quietly = TRUE)
}

arcgisbinding::arc.check_product()

use_package('ForestTools')
use_package('stats')
use_package('rgdal')
use_package('raster')
use_package('sf')
use_package('arcgisbinding')

#' This function runs when this file is used as an
#' ArcGIS Pro toolbox script
tool_exec <- function(in_params, out_params) {
  #############################################################################
  ###### inputs and outputs ###################################################
  #############################################################################
  
  # read inputs
  opened_input_canopy_raster = arcgisbinding::arc.open(in_params$Input_Tree_Canopy_Height_Raster)
  input_canopy_raster = arcgisbinding::arc.raster(opened_input_canopy_raster)
  input_min_tree_height = in_params$Input_Minimum_Tree_Height
  input_min_crown_height = in_params$Input_Minimum_Crown_Height
  crs = opened_input_canopy_raster@sr[['WKT']]
  window_function = in_params$WINDOW_FUNCTION

  # read output paths
  output_treetop_path = out_params[[1]]
  output_crown_polygon_path <- out_params[[2]]
  
  #############################################################################
  ##### Generate tree tops ####################################################
  #############################################################################
  message(' ')
  message('⏳ Generating tree points')

  # convert the input canopy raster reference to a spacial data frame
  cat('Converting input tree canopy height raster to a spacial data frame... ')
  canopy_spacial_data_frame = arcgisbinding::arc.data2sp(input_canopy_raster)
  message('✔ DONE')
  
  # get the canopy height model as a raster
  cat('Converting spacial data frame to canopy height model (CHM) raster... ')
  canopy_height_model_raster = raster::raster(canopy_spacial_data_frame)
  message('✔ DONE')
  
  # construct the window function for the variable window filer algorithm
  linear_function = function(x) { eval(parse(text=window_function)) }
  
  # calculate treetops
  message('Calculating treetops using the variable window filter algorithm (Popescu & Wynne, 2004) for detecting treetops from a canopy height model... ')
  treetops = ForestTools::vwf(
                CHM = canopy_height_model_raster,
                minHeight = input_min_tree_height,
                minWinNeib = 'queen',
                winFun = linear_function,
                maxWinDiameter = NULL,
                verbose = TRUE
              )
  message('✔ DONE')
  
  # assign coordinate system
  cat('Assigning coordinate system... ')
  treetops_sf = sf::st_as_sf(treetops) # convert from sp to sf package format
  treetops_sf_with_crs = sf::st_set_crs(treetops_sf, crs)
  message('✔ DONE')
  
  # tell arcgis to write treetops to output path
  cat('Saving treetops shapefile... ')
  sf::write_sf(treetops_sf_with_crs, output_treetop_path)
  message('✔ DONE')
  
  # return early if variables required for generating crown polygons are null
  # (they are optional since generating crown polygons takes a while)
  if (is.null(output_crown_polygon_path) || is.null(input_min_crown_height)) {
    message('⚠ Skipped generating crown polygons because no output path was provided')
    message('✅ DONE')
    return(out_params)
  }

  #############################################################################
  ##### Generate Crown Polygons ###############################################
  #############################################################################
  message(' ')
  message('⏳ Generating crown polygons')
  
  # generate crown polygons
  message('Generating crown polygons based on treetops via watershed segmentations... ')
  crowns <- ForestTools::mcws(treetops = treetops, format = "polygons", CHM = canopy_height_model_raster, minHeight = input_min_tree_height - 0.01, verbose = TRUE)
  message('✔ DONE')
  
  # assign coordinate system
  cat('Assigning coordinate system... ')
  crowns_sf = sf::st_as_sf(crowns) # convert from sp to sf package format
  crowns_sf_with_crs = sf::st_set_crs(crowns_sf, crs)
  crowns_with_crs = as(crowns_sf_with_crs, "Spatial")
  message('✔ DONE')
  
  # tell arcgis to write crown polygons to output path
  cat('Queing crown polygons to be saved...')
  arcgisbinding::arc.write(output_crown_polygon_path, crowns_with_crs)
  message('✔ DONE')
  
  # return the output data
  message('✅ DONE')
  return(out_params)
}