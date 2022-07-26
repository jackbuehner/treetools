options(install.packages.check.source = 'no')

options("rgdal_show_exportToProj4_warnings" = "none") # hide proj4 warnings

oldwl = getOption("warn")
options(warn = -1)

use_package = function(p) {
  if (!is.element(p, installed.packages()[, 1])) {
    message('Installing package: ', p)
    install.packages(p, repos = 'https://archive.linux.duke.edu/cran/', type = 'both')
  }
  require(p, quietly = TRUE)
}

use_package('stats')
use_package('lidR')
use_package('rgdal')
use_package('sf')
use_package('dplyr')
use_package('arcgisbinding')
use_package('RCSF')

#' This function runs when this file is used as an
#' ArcGIS Pro toolbox script
tool_exec = function(in_params, out_params) {
  if (in_params$CLIP_VEGETATION == TRUE && is.null(in_params$VEGETATION_POLY)) {
    stop('Must provide vegetation polygon shapefile path when CLIP_VEGITATION == TRUE')
  }

  # generate the filtered LiDAR
  filtered_las = prune_buildings_from_las(
    las_file_path = in_params$LAS, 
    buildings_layer_folder = dirname(in_params$BUILDINGS), 
    buildings_layer_name = basename(in_params$BUILDINGS),
    buildings_attr_top_elev =  in_params$BUILDINGS_ATTR_TOP_ELEV,
    above_building_buffer =  in_params$ABOVE_BUILDING_BUFFER
  )

  # optionally clip to only include areas with vegetation
  if (in_params$CLIP_VEGETATION == TRUE) {
    filtered_las = clip_vegetation(filtered_las, dirname(in_params$VEGETATION_POLY), basename(in_params$VEGETATION_POLY))
  }

  # optionally remove planar points (e.g. walls or elevated parking lots)
  if (in_params$REMOVE_PLANAR == TRUE) {
    filtered_las = remove_planar_points(filtered_las)
  }
  
  # save the filtered LiDAR
  lidR::writeLAS(filtered_las, out_params$FILTERED_LAS, index = FALSE)
}


#' Prune LiDAR points that fall within a 3D building polygon.
#' 
#' Points within the 2D polygon are flagged, and they are
#' only removed if their elevation is less than the highest point
#' of the building.
#' 
#' The highest point of the building can be manipulated by
#' specifying ABOVE_BUILDING_BUFFER. It defaults to 5 to
#' help eliminate rooftop equipment.
prune_buildings_from_las = function(las_file_path, buildings_layer_folder, buildings_layer_name, buildings_attr_top_elev, above_building_buffer) {
  message(' ')
  message('⏳ Pruning LiDAR points that fall within 3D building polygons')

  #=======================================================================#
  # Import LAS file
  #=======================================================================#
  cat('Loading LiDAR file... ')
  las = lidR::readLAS(las_file_path)
  las_crs = sf::st_crs(las)
  message('✔ DONE')

  out = tryCatch({
    #=======================================================================#
    # Import and process buildings shapefile
    #=======================================================================#
    cat('Loading buildings shapefile... ')
    buildings_spdf = rgdal::readOGR(buildings_layer_folder, sub('.shp', '', buildings_layer_name))
    message('✔ DONE')
  
    cat('Transforming buildings to sf type... ')
    buildings_sf = sf::st_as_sf(buildings_spdf)
    message('✔ DONE')
    
    cat('Converting buildings coordinate system to match LiDAR... ')
    buildings = sf::st_transform(buildings_sf, las_crs)
    buildings = dplyr::rename(buildings, bldgTopElev = dplyr::all_of(buildings_attr_top_elev))
    message('✔ DONE')
    
    cat('Recaclulating building tops... ')
    buildings$bldgTopElev = buildings$bldgTopElev + above_building_buffer
    message('✔ DONE')
    
    #=======================================================================#
    # Perform spacial merge between LiDAR and buildings
    #=======================================================================#
    cat('Performing spatial merge with building polygons... ')
    las_with_buildings_markers = lidR::merge_spatial(las, buildings, 'inBuildingPolygon')
    las_with_buildings_markers = lidR::merge_spatial(las_with_buildings_markers, buildings, 'bldgTopElev')
    message('✔ DONE')
    
    #=======================================================================#
    # Filter buildings out of the LiDAR
    #=======================================================================#
    cat('Filtering buildings out of LiDAR... ')
    filtered_las = lidR::filter_poi(las_with_buildings_markers, is.na(bldgTopElev) | Z > bldgTopElev) # nolint
    message('✔ DONE')

    #=======================================================================#
    # Return the filtered LiDAR
    #=======================================================================#
    message('✅ DONE')
    return(filtered_las)
  }, error = function(error) {
    #=======================================================================#
    # Return the original LiDAR (something went wrong)
    #=======================================================================#
    message('Something went wrong. Returning the original LiDAR... ')
    message('✅ DONE')
    return(las)
  })

  return(out)
}

#' Clip LiDAR points to a vegetation shapefile.
#' 
#' The vegetation shapefile should only contain one polygon
#' that represents vegetated areas.
clip_vegetation = function(las, vegetation_layer_folder, vegetation_layer_name) {
  message(' ')
  message('⏳ Clipping LiDAR to only include points within the provided vegetation shapefile')

  las_crs = sf::st_crs(las)

  out = tryCatch({
    #=======================================================================#
    # Import and process vegetation shapefile
    #=======================================================================#
    cat('Loading vegetation shapefile... ')
    veg_poly_spdf = rgdal::readOGR(vegetation_layer_folder, sub('.shp', '', vegetation_layer_name))
    message('✔ DONE')
    
    cat('Transforming vegetation to sf type... ')
    veg_poly_sf = sf::st_as_sf(veg_poly_spdf)
    message('✔ DONE')
    
    cat('Converting vegetation coordinate system to match LiDAR... ')
    veg_poly = sf::st_transform(veg_poly_sf, las_crs)
    message('✔ DONE')

    #=======================================================================#
    # Perform spacial merge between LiDAR and vegetation
    #=======================================================================#
    cat('Performing spatial merge with vegetation polygons... ')
    las_with_vegetation_markers = lidR::merge_spatial(las, veg_poly, 'veg')
    message('✔ DONE')

    #=======================================================================#
    # Filter unvegetated regions out of the LiDAR
    #=======================================================================#
    cat('Removing unvegetated regions from LiDAR... ')
    filtered_las = lidR::filter_poi(las_with_vegetation_markers, veg == TRUE)
    message('✔ DONE')
    
    #=======================================================================#
    # Return the filtered LiDAR
    #=======================================================================#
    message('✅ DONE')
    return(filtered_las)
  }, error = function(error) {
    #=======================================================================#
    # Return the original LiDAR (something went wrong)
    #=======================================================================#
    message('Something went wrong. Returning the original LiDAR... ')
    message('✅ DONE')
    return(las)
  })

  return(out)
}

#' Remove planar points from LiDAR.
remove_planar_points = function(las) {
  message(' ')
  message('⏳ Removing planar points from LiDAR')

  # apply a boolean plane attribute to planar points (e.g. building tops or tall walls)
  # (shp_hplane removes planes on the x-, y-, and z-axis)
  cat('Identifying planar points...')
  segmented_las = lidR::segment_shapes(las, lidR::shp_hplane(k = 20), "plane")
  message('✔ DONE')

  # filter LiDAR to exclude planar points
  cat('Removing planar points...')
  filtered_las = lidR::filter_poi(segmented_las, plane != TRUE)
  message('✔ DONE')

  # return the filtered LiDAR 
  message('✅ DONE')
  return(filtered_las)
}

normalize_las = function(las) {
  cat('Normalizing point cloud: classifying ground points (expensive) [1/2]')
  message('✔ DONE')
  classified_las = lidR::classify_ground(las, lidR::csf())
  cat('Normalizing point cloud: normalizing based on ground points [2/2]')
  normalized_las = lidR::normalize_height(classified_las, lidR::tin())
  message('✔ DONE')
  return(normalized_las)
}

las_to_chm = function(las, normalize = TRUE) {
  #=======================================================================#
  # Normalize point cloud elevations
  #=======================================================================#
  if (normalize == TRUE) {
    las = normalize_las(las)
  }

  #=======================================================================#
  # Normalize point cloud elevations
  #=======================================================================#
  chm = lidR::rasterize_canopy(las, res = 1.1, algorithm = lidR::pitfree())
  lidR::plot(chm)
}

options(warn = oldwl)

# chm = lasToChm(lidR::readLAS('D:/jackbuehner/Summer2022/GIS/ArcGIS/Lidar_tree_canopy_points_test/LAS/original/5180-03_iPickedThisSquare.las'), FALSE)

# filteredLAS = pruneBuildingsFromLas(
#     LAS_FILE_PATH = 'D:/jackbuehner/Summer2022/GIS/ArcGIS/Lidar_tree_canopy_points_test/LAS/original/5180-03_iPickedThisSquare.las', 
#     BUILDINGS_LAYER_FOLDER = 'D:/jackbuehner/Summer2022/GIS/ArcGIS/Lidar_tree_canopy_points_test', 
#     BUILDINGS_LAYER_NAME = 'iPickedThisSquare_buildings_buffer.shp',
#     BUILDINGS_ATTR_TOP_ELEV = 'TOPELEV',
#     ABOVE_BUILDING_BUFFER = 5
#   )

# # classify ground and normalize height
# #filteredLAS = lidR::classify_ground(filteredLAS, lidR::csf())
# #normalizedFilteredLAS = lidR::normalize_height(filteredLAS, lidR::tin())

# # clip to only include areas with vegitation
# vegPolyPath = 'D:/jackbuehner/Summer2022/GIS/ArcGIS/Lidar_tree_canopy_points_test/ndvi_veg_polygon_iPickedThisSquare'
# filteredLAS = clipVegetation(filteredLAS, dirname(vegPolyPath), basename(vegPolyPath))

# # expiriment with removing planar points (maybe add this as a condition?)
# # shp_hplane removes planes on the x-, y-, and z-axis
# filteredLAS = removePlanarPoints(filteredLAS)

# lasToChm(filteredLAS, FALSE)

# # classify noise ---- not really helpful
# #filteredLAS = lidR::classify_noise(filteredLAS, lidR::ivf(res = 5, n = 6))

# plot(filteredLAS)
