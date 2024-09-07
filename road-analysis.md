## Analysis of Road dataset with flood 2yr 

### Install 
- Install Postgresql
- Install python
- Install gdal
- Install Postgis and postgis_h3 extension
- Install osm2pgsql

## Process OSM Data 

```bash
osm2pgsql --create nepal-latest.osm.pbf -U admin -W -d postgres -E 4326
```
Logs Summary
```log
2024-09-06 23:39:59  osm2pgsql version 1.11.0
2024-09-06 23:39:59  Database version: 14.13 (Homebrew)
2024-09-06 23:39:59  PostGIS version: 3.4
2024-09-06 23:51:06  Analyzing table 'planet_osm_polygon'...
2024-09-06 23:53:55  All postprocessing on table 'planet_osm_polygon' done in 708s (11m 48s).
2024-09-06 23:53:55  All postprocessing on table 'planet_osm_roads' done in 9s.
2024-09-06 23:53:55  Storing properties to table '"public"."osm2pgsql_properties"'.
2024-09-06 23:53:56  osm2pgsql took 837s (13m 57s) overall.
```


Create `roads` table 
```sql
create table roads 
as ( 
select name , highway , way as geometry
from planet_osm_roads);
```

Drop unneccesary tables 
```sql
drop table planet_osm_line;
drop table planet_osm_point;
drop table planet_osm_polygon;
drop table osm2pgsql_properties;
drop table planet_osm_roads;
```

Create index on roads geom 
```sql
create index on roads(geometry);
```

Generate h3 index for roads 
```sql
ALTER TABLE roads ADD COLUMN h3_ix h3index GENERATED ALWAYS AS (h3_lat_lng_to_cell(ST_Centroid(geometry), 8)) STORED;
```
Using centroid might not always be ideal for line features , you might consider using array of h3 indexes to be stored 

if you want to store h3cell for all points you can use this function 
```sql
CREATE OR REPLACE FUNCTION get_h3_cells_for_linestring(
    geom geometry,
    h3_resolution integer
)
RETURNS h3index[] AS $$
DECLARE
    h3_indexes h3index[];
    point geometry;
BEGIN
    h3_indexes := ARRAY[]::h3index[];

    FOR point IN
        SELECT (ST_DumpPoints(ST_LineMerge(geom))).geom
    LOOP
        h3_indexes := array_append(h3_indexes, h3_lat_lng_to_cell(point, h3_resolution));
    END LOOP;

    RETURN array_agg(DISTINCT h3_indexes);
END;
$$ LANGUAGE plpgsql;
```

In array h3 index case to generate list of h3indexes
```sql
ALTER TABLE roads ADD COLUMN h3_ix_array h3index[];

UPDATE roads
SET h3_ix_array = get_h3_cells_for_linestring(geometry, 8);
```

Generate tiles for roads 
```bash
ogr2ogr -f MVT roads PG:"user=admin dbname=postgres password=admin" "roads" -t_srs EPSG:3857 -dsco COMPRESS=NO -dsco MAXZOOM=16 -progress
```



## Process flood5yr data 
Find preprocessing automation .sh [here](https://github.com/kshitijrajsharma/cog2h3/blob/main/pre.sh) :

- Download 

### Preprocess 
```bash 
sudo bash pre.sh /Users/krschap/probono/workshop-dristi/data/5yr_flood_extent_cog.tif
```

Logs : 
```log
Reprojecting /Users/krschap/probono/workshop-dristi/data/5yr_flood_extent_cog.tif to EPSG:4326...
Creating output file that is 5762P x 3051L.
Using internal nodata values (e.g. 0) for image /Users/krschap/probono/workshop-dristi/data/5yr_flood_extent_cog.tif.
Copying nodata values from source /Users/krschap/probono/workshop-dristi/data/5yr_flood_extent_cog.tif to destination 5yr_flood_extent_cog_reprojected.tif.
Processing /Users/krschap/probono/workshop-dristi/data/5yr_flood_extent_cog.tif [1/1] : 0...10...20...30...40...50...60...70...80...90...100 - done.
Setting nodata values to 0...
Creating output file that is 5762P x 3051L.
Using internal nodata values (e.g. 0) for image 5yr_flood_extent_cog_reprojected.tif.
Processing 5yr_flood_extent_cog_reprojected.tif [1/1] : 0...10...20...30...40...50...60...70...80...90...100 - done.
Converting to COG format...
Input file size is 5762, 3051
0...10...20...30...40...50...60...70...80...90...100 - done.
Processing complete. Output file: 5yr_flood_extent_cog_preprocessed.tif
```

### Process 

Export your DB credentials 
```bash
export DATABASE_URL="postgresql://admin:admin@localhost:5432/postgres"
```

Run 

```bash
cog2h3 --cog 5yr_flood_extent_cog_preprocessed.tif --table yr5flood --res 8
```
Here we are using max res 15 , however script will determine the minimum fitting res and process the data 
```log
2024-09-06 23:08:42,145 - INFO - Starting processing
2024-09-06 23:08:42,146 - INFO - COG file already exists at 5yr_flood_extent_cog_preprocessed.tif
2024-09-06 23:08:42,146 - INFO - Processing raster file: 5yr_flood_extent_cog_preprocessed.tif
2024-09-06 23:08:42,355 - INFO - Determined Min fitting H3 resolution for band 1: 10
2024-09-06 23:08:42,355 - WARNING - Supplied res 15 is higher than native resolution, Upscaling raster is not supported yet, hence falling back to 10
2024-09-06 23:08:47,871 - INFO - Calculation done for res:10 band:1
2024-09-06 23:08:47,906 - INFO - Converting H3 indices to hex strings
2024-09-06 23:08:48,997 - INFO - Overall raster calculation done in 6 seconds
2024-09-06 23:08:48,998 - INFO - Creating or replacing table yr5flood in database
2024-09-06 23:09:09,346 - INFO - Table yr5flood created or updated successfully in 20.35 seconds.
2024-09-06 23:09:09,649 - INFO - Processing completed
```
Here our min fitting resolution is 10, for proeuction 10 is recommended . To create simplicity on this workshop  we will work on 8.

### Post Process

lets create some indexes 
```sql
create index on yr5flood(h3_ix);
```

lets create geometry of those index cell for visualization ( This won't be needed if tiling is to be done directly from the API ) 

```sql
ALTER TABLE yr5flood  
ADD COLUMN geometry geometry(Polygon, 4326) 
GENERATED ALWAYS AS (h3_cell_to_boundary_geometry(h3_ix)) STORED;
```


create index on geometry column 
```sql
create index on yr5flood(geometry);
```

Visualize in QGIS : 
<img width="1430" alt="image" src="https://github.com/user-attachments/assets/de07b4c0-3d87-4022-b570-306dc3090f50">


### Tile generation

Now lets create tile for the table  
```bash 
ogr2ogr -f MVT yr5flood PG:"user=admin password=admin" "yr5flood" -t_srs EPSG:3857 -dsco COMPRESS=NO -dsco MAXZOOM=18 -progress
```
This tile generation part will take some time as it will generate the static tile for all geomtry at once , however this can made dymaic with the generating tiles on request from fastAPI on future


## Analysis 

lets get flood5yr data on roads dataset 
```sql
ALTER TABLE roads
ADD COLUMN flood5yr FLOAT;
```

Update the flood5yr column 
```sql
UPDATE roads
SET flood5yr = f.band1
FROM yr5flood f
WHERE roads.h3_ix = f.h3_ix;
```

Lets get affected road part by flood5yr extent its length in meters, location and exact part
```sql 
with t1 as (
select h3_ix ,band1
from yr5flood yf 
where band1 >2 ),
t2 as (
select * , st_intersection(r.geometry,h3_cell_to_boundary_geometry(t1.h3_ix)) as affected_road
from roads r , t1 
where t1.h3_ix = ANY(r.h3_ix_array) and r.highway  is not null
) 
select t2.geometry as road_actual_geometry , t2.affected_road as geometry, t2.highway , t2.name ,  t2.band1 as flood5yr, ST_Length(t2.affected_road::geography) as affected_road_length_m
from t2
```




