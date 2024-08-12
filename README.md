# raster-using-h3
Raster analysis with ease using h3 indexes


## Objective 
For learning, We will do calculation on figuring out how many buildings are there in settlement area determined by ESRI Land Cover. Lets aim of national level data for both vector and raster . 

## Let's first find the data 

### Download Raster Data 

I have downloaded the settlement area from Esri Land Cover .

- https://livingatlas.arcgis.com/landcover/ 

Lets download the 2023 year , of size approx 362MB

<img width="1378" alt="image" src="https://github.com/user-attachments/assets/a4611ebb-a2fb-4c00-a490-b3f0798f50f9">


### Download OSM Buildings of Nepal 

Source : http://download.geofabrik.de/asia/nepal.html
```shell
wget http://download.geofabrik.de/asia/nepal-latest.osm.pbf
```

## Preprocess the data 
Lets apply some preprocessing to data before actual h3 cell calculations
We will be using [gdal](https://gdal.org/index.html)  commandline program for this step. [Install gdal](https://gdal.org/download.html) in your machine 

### Conversion to Cloud Optimized Geotiff
If you are unaware of cog , Checkout here : https://www.cogeo.org/ 

Check if gdal_translate is available 
```shell
gdal_translate --version
```
It should print the gdal version you are using 
Now lets convert tif to cloud optimized geotif
```shell
gdal_translate -of COG esri-settlement-area-kathmandu-grid.tif esri-landcover-cog.tif
```
It took less than a minute to convert that tiff to geotiff , However the downloaded tiff was already on cog format . ( Do this process if you have normal geotif ) 

### Insert osm data to postgresql table 

We are using [osm2pgsql](https://osm2pgsql.org/doc/install.html) to insert osm data to our table 

```shell
osm2pgsql --create nepal-latest.osm.pbf -U postgres
```
osm2pgsql took 274s (4m 34s) overall.

You can use geojson files also if you have any using ogr2ogr 
```shell
ogr2ogr -f PostgreSQL  PG:"dbname=postgres user=postgres password=postgres" buildings_polygons_geojson.geojson -nln npl_buildings
```
ogro2gr has wide range of support for [drivers](https://gdal.org/drivers/vector/index.html) so you are pretty flexible about what your input is  . Output is Postgresql table 

## Calculate h3 indexes 

###  Postgresql
Install 
```shell
pip install pgxnclient cmake
pgxn install h3
```
Create extension in your db 
```sql
create extension h3;
create extension h3_postgis CASCADE;
```
Now lets get the buildings table
```
CREATE TABLE buildings (
  id SERIAL PRIMARY KEY,
  osm_id BIGINT,
  building VARCHAR,
  geometry GEOMETRY(Polygon, 4326)
);
```
Insert data to table
```sql
INSERT INTO buildings (osm_id, building, geometry)
SELECT osm_id, building, way
FROM planet_osm_polygon pop
WHERE building IS NOT NULL;
```

Log and timing : 
```log
Updated Rows	8048542
Query	INSERT INTO buildings (osm_id, building, geometry)
	SELECT osm_id, building, way
	FROM planet_osm_polygon pop
	WHERE building IS NOT NULL
Start time	Mon Aug 12 08:23:30 NPT 2024
Finish time	Mon Aug 12 08:24:25 NPT 2024
```


Now lets calculate the h3 indexes for those buildings using centroid
```
ALTER TABLE buildings ADD COLUMN h3_index h3index GENERATED ALWAYS AS (h3_lat_lng_to_cell(ST_Centroid(geometry), 8)) STORED;
```




### Raster operations


