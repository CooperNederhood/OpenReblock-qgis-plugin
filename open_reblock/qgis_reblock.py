from pathlib import Path 

import sys 

ROOT = Path(__file__).resolve().parent
PRCLZ_PATH = ROOT / "prclz"

sys.path.insert(0, str(PRCLZ_PATH))
PRCLZ_PATH = Path(PRCLZ_PATH) / "prclz"
sys.path.insert(0, str(PRCLZ_PATH))
# Import reblocking utils
from prclz.i_reblock import *
from prclz.i_topology_utils import *

from shapely.wkt import loads  
from qgis.PyQt.QtCore import QVariant
#from qgis._core import QgsVectorLayer
from shapely.geometry import MultiPolygon, MultiPoint
from typing import List, Union

from qgis.core import QgsVectorLayer, QgsProject, QgsField, QgsGeometry, QgsFeature, QgsExpression, QgsFeatureRequest
from qgis.PyQt.QtCore import QVariant

import logging 
logger = logging.getLogger('reblock_application')
logger.setLevel(logging.DEBUG)
 
def check_layer_has_block_field(qgis_layer: QgsVectorLayer, 
                                  block_id: str) -> bool:
    '''
    Check whether or not the block_id field name is present
    in the current QGIS layer
    '''
    for f in qgis_layer.fields():
        if f.name() == "block_id":
            return True 
    return False 

# create layer
def shapely_geom_to_layer(geom: MultiPolygon, layer_name='Reblocking'):
    '''
    NOTE: assumes geom is MultiPolygon
    resulting from Steiner algorithm
    '''
    vl = QgsVectorLayer("MultiLineString", layer_name, "memory")
    pr = vl.dataProvider()
    # add fields
    pr.addAttributes([QgsField("block_id", QVariant.String)])
    # pr.addAttributes([QgsField("block_id", QVariant.String),
    #                     QgsField("age",  QVariant.Int),
    #                     QgsField("size", QVariant.Double)])
    vl.updateFields() # tell the vector layer to fetch changes from the provider
    # add a feature
    fet = QgsFeature()
    fet.setGeometry(QgsGeometry.fromWkt(geom.wkt))
    #fet.setAttributes(["DJI.5.1_1"])
    fet.setAttributes(['TEST'])
    pr.addFeatures([fet])
    # update layer's extent when new features have been added
    # because change of extent in provider is not propagated to the layer
    vl.updateExtents()
    #QgsMapLayerRegistry.instance().addMapLayers([vl])
    QgsProject.instance().addMapLayer(vl)
    return vl 


def multipoint_to_point_list(multipoint: MultiPoint):

    point_list = [list(point.coords) for point in multipoint]
    return [x[0] for x in point_list]

def do_reblock(parcel_geom, building_list: List, block_geom=None):
    '''
    Sipmle reblocking for a single block

    TO-DO: does not include weighting of parcel 
    '''
    print('Creating planar graph...')
    planar_graph = PlanarGraph.multilinestring_to_planar_graph(parcel_geom)
    print('...planar graph created!')

    # Update the edge weight
    if block_geom is not None:
        building_list = add_outside_node(block_geom, building_list)
        missing, total_block_coords = i_topology_utils.update_edge_types(planar_graph, block_geom, check=True)

    print('Starting optimal path estimation...')
    new_steiner, existing_steiner, terminal_points, summary = get_optimal_path(planar_graph, building_list, simplify=True, verbose=True)
    return new_steiner, existing_steiner


def get_geom_from_qgis_layer(qgis_layer: QgsVectorLayer, 
                               block_id: str) -> Union[MultiPoint, MultiPolygon, MultiLineString]:
    '''
    Get's features from layer, then gets geom, then converts
    to wkt, then to shapely
    '''
    exp_str = "block_id ILIKE \'{}\'".format(block_id)
    exp = QgsExpression(exp_str)
    #exp = QgsExpression('gadm_code ILIKE \'%DJI.1.1_1%\'')
    request = QgsFeatureRequest(exp)
    features = list(qgis_layer.getFeatures(request))
    all_geoms = [loads(f.geometry().asWkt()) for f in features]
    return all_geoms 

def get_bulding_inputs(building_layer: QgsVectorLayer, block_id: str) -> MultiPoint:
    '''
    Extracts the inputs from the QGIS building_layer in shapely format
    so that we can run reblocking

    Inputs:
        - building_layer: (QGIS layer) buildings
    Returns:
        - building_centroids: (Shapely MultiPoint) building centroids
    '''
    building_geoms = get_geom_from_qgis_layer(building_layer, block_id)
    if len(building_geoms) == 0:
        building_centroids = None
    else:
        building = building_geoms[0]
        # test 
        if isinstance(building, MultiPolygon):
            building_centroids = []
            for multi_poly in building_geoms:
                for poly in multi_poly:
                    building_centroids.append(poly.centroid)
        elif isinstance(building, Polygon):
            building_centroids = []
            for poly in building_geoms:
                building_centroids.append(poly.centroid)
        else:
            print("bulding type is {}".format(type(building)))
        building_centroids = MultiPoint(building_centroids)
    return building_centroids

def get_parcel_inputs(parcel_layer: QgsVectorLayer, block_id: str) -> MultiLineString:
    '''
    Extracts the inputs from the QGIS parcels_layer in shapely format
    so that we can run reblocking

    Inputs:
        - parcels_layer: (QGIS layer) parcels
    Returns:
        - parcel_multilinestring: (Shapely MultiLineString) parcels
    '''
    parcel_geoms = get_geom_from_qgis_layer(parcel_layer, block_id)
    parcel = parcel_geoms[0]
    #
    if isinstance(parcel, LineString):
        parcel_multilinestring = MultiLineString(parcel_geoms)
    elif isinstance(parcel, MultiLineString):
        assert len(parcel_geoms) == 1, "ERROR -- check Parcel Geom is MultiLineString but not unique"
        parcel_multilinestring = parcel_geoms[0]
    else:
        print("parcel type is {}".format(type(parcel)))
    return parcel_multilinestring

def make_qgis_reblock_layers(building_layer: QgsVectorLayer, parcel_layer: QgsVectorLayer, 
                             target_block_list: List[str],
                             block_layer=None, id_col='block_id', output_layer_name="reblock"):
    '''
    Main reblocking function to be called from QGIS plugin.
    Inputs are two QGIS layers.

    Inputs:
        - building_layer: (QGIS layer) buildings
        - parcel_layer: (QGIS layer) parcels
        - id_col: (str) name of feature column which identifies the unit of a
                        analysis to match buildings and parcels
    ''' 

    # TO-DO: can this be accessed w/o for-loop?
    # block_set = {ft[id_col] for ft in parcel_layer.getFeatures()}
    # block_list = list(block_set)
    block_list = target_block_list

    new_steiner_geoms = []
    existing_steiner_geoms = []

    # Check
    for qgis_layer in [building_layer, parcel_layer]:
        has_block_field = check_layer_has_block_field(qgis_layer, id_col)
        assert has_block_field, "ERROR: layer {} does not have field {}, which is needed to map the geometries to a specific block".format(qgis_layer.name(), id_col)
    if block_layer is not None:
        assert check_layer_has_block_field(block_layer, id_col), "ERROR: layer {} does not have field {}, which is needed to map the geometries to a specific block".format(block_layer.name(), id_col)


    print("in qgis_reblock: block count = {}".format(len(block_list)))

    for block_id in block_list:
        print("in qgis_reblock: processing block_id = {}".format(block_id))

        # (1) Get buildings
        building_centroids = get_bulding_inputs(building_layer, block_id)
        if building_centroids is None:
            print("centroids is none...")
            continue 
        building_list = multipoint_to_point_list(building_centroids)

        # (2) Get parcels
        parcel_geom = get_parcel_inputs(parcel_layer, block_id)

        # (3) Get block (i.e. existing roads)
        block_geom = get_geom_from_qgis_layer(block_layer, block_id)[0] if block_layer is not None else None

        # Drop buildings that intersect with block (i.e. existing roads)
        if block_geom is not None:
            building_list = drop_buildings_intersecting_block(parcel_geom, building_list, block_geom, block_id)

        # Can't reblock if only 1 building
        if len(building_list) <= 1:
            print("Skipping block {} with {} buildings".format(block_id, len(building_centroids)))
            continue

        print("Working on block {} with {} buildings".format(block_id, len(building_centroids)))
        new_steiner, existing_steiner = do_reblock(parcel_geom, building_list, block_geom)
        new_steiner_geoms.append(new_steiner)
        existing_steiner_geoms.append(existing_steiner)

    new_steiner = unary_union(new_steiner_geoms)
    existing_steiner = unary_union(existing_steiner_geoms)

    # Join into a single shapely geom and convert to a QGIS layer 
    new_steiner_layer = shapely_geom_to_layer(new_steiner, output_layer_name)
    #existing_steiner_layer = shapely_geom_to_layer(new_steiner, "Existing_roads")


# SLE.4.2.1_1_1632

# import sys 
# sys.path.insert(0, "/home/cooper/Documents/chicago_urban/mnp/prclz-proto/prclz")
# import qgis_reblock 

# layers = QgsProject.instance().layerTreeRoot().children()
# l0 = layers[0].layer()
# l1 = layers[1].layer()


#     all_blocks = [b for b in possible_buildings if b not in checkpointer.completed]

#     print("\nBegin looping")
#     i = 0
#     elapsed_time_mins = -np.inf 
#     if mins_threshold is None:
#         mins_threshold = np.inf 
#     # (4) Loop and process one block at-a-time
#     for block_id in tqdm.tqdm(all_blocks, total=len(all_blocks)):

#         # Approx time of completion of block
#         start_time = time.time()

#         # If most recent block took over our minute cutoff, break and finish
#         #print("threshold is {}, most recent is {}".format(mins_threshold, elapsed_time_mins))
#         if elapsed_time_mins > mins_threshold:
#             print("Took {} mins and threshold is {} mins -- ending gadm at {}".format(elapsed_time_mins, mins_threshold, block_id))
#             checkpointer.save()
#             break 

#         parcel_geom = parcels[parcels['block_id']==block_id]['geometry'].iloc[0]
#         building_list = buildings[buildings['block_id']==block_id]['buildings'].iloc[0]
#         block_geom = blocks[blocks['block_id']==block_id]['geometry'].iloc[0]

#         ## UPDATES: drop buildings that intersect with the block border -- they have access
#         if len(building_list) <= 1:
#             continue 

#         building_list = drop_buildings_intersecting_block(parcel_geom, building_list, block_geom, block_id)

#         ## And explicitly add a dummy building outside of the block which will force Steiner Alg
#         #      to connect to the outside road network
#         bounding_rect = block_geom.minimum_rotated_rectangle
#         convex_hull = block_geom.convex_hull
#         outside_block = bounding_rect.difference(convex_hull)
#         outside_building_point = outside_block.representative_point()
#         building_list.append(outside_building_point.coords[0])

#         if len(building_list) <= 1:
#             continue 

#         # (1) Convert parcel geometry to planar graph
#         planar_graph = PlanarGraph.multilinestring_to_planar_graph(parcel_geom)

#         # (2) Update the edge types based on the block graph
#         missing, total_block_coords = i_topology_utils.update_edge_types(planar_graph, block_geom, check=True)

#         # (3) Do reblocking 
#         try:
#             new_steiner, existing_steiner, terminal_points, summary = get_optimal_path(planar_graph, building_list, simplify=simplify, verbose=True)
#         except:
#             new_steiner = None 
#             existing_steiner = None 
#             terminal_points = None 
#             summary = [None, None, None, None, None, None, None, None]

#         elapsed_time_mins = (time.time() - start_time)/60

#         # Collect and store the summary info from reblocking
#         summary = summary + [len(building_list), total_block_coords, missing, block_id]
#         checkpointer.update(block_id, new_steiner, existing_steiner, terminal_points, summary)

#         # Save out on first iteration and on checkpoint iterations
#         if (i == 0) or (i % checkpoint_every == 0):
#             checkpointer.save()

             
#         i += 1
