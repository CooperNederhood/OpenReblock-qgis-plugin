# OpenReblock-qgis-plugin
QGIS3 plugin of reblocking utilities 

# Initial Setup
**1. Install QGIS**
https://www.qgis.org/en/site/forusers/alldownloads.html

**2. Install Open Reblock plugin**
In QGIS, open the plugin manager via: "Plugins" >> "Manage and Install Plugins..."

Next, searching for "reblock" should return the Open Reblock plugin. Install!

# Reblocking Walkthrough

## Reblocking inputs
**1. Block layer**

The block layer is the *existing* city streets. It should be a polygon format.

![Alt text](https://github.com/CooperNederhood/OpenReblock-qgis-plugin/blob/master/how_to/s0_block_data.png "Title")


**2. Building layer**

We then need footprints of the *existing* city buildings. It should be a polygon format.

We define a city "block" as an area fully circumscribed by some road network. As you can see, some buildings have direct access to the existing road network and others are interior parcels and lack direct access. We will use Open Reblock to "grow" new streets so that each building has direct street access.

![Alt text](https://github.com/CooperNederhood/OpenReblock-qgis-plugin/blob/master/how_to/s1_building_data.png "Title")

**3. Parcel layer**

Finally, we need parcel lines dividing each building. These parcel boundaries will be the candidates for the road network we grow. The Reblocking Algorithm with propose the set of parcels that: (1) provide direct street access to every building and (2) do so with the least amount of new roads.

![Alt text](https://github.com/CooperNederhood/OpenReblock-qgis-plugin/blob/master/how_to/s2_parcel_data.png "Title")

