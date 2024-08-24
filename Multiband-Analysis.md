# Process multiband rasters (Sentinel-2) with h3 index and create indices 

Hi, In previous [blog](https://dev.to/krschap/raster-analysis-using-uber-h3-indexes-and-postgresql-57g9) we talked about how we can do raster analysis using h3 indexes and postgresql for a single band raster. In this blog we will talk about how we can process multiband raster and create indices with ease. We will be using sentinel-2 image and create NDVI from the processed h3 cells and visualize the results

## Download sentinel 2 data

We are downloading the sentinel 2 data from https://apps.sentinel-hub.com/eo-browser/ in Pokhara, Nepal Area , Just to make sure lake is in the image grid so that it would be easy for us to validate the NDVI result

<img width="1263" alt="image" src="https://github.com/user-attachments/assets/f0d7b402-d2e7-473b-940e-57f3a5db254c">

To download sentinel image with all bands : 

- You need to create an account 
- Find the image in your area select the grid that covers your Area of interest 
- Zoom to the grid, And click on <img width="74" alt="image" src="https://github.com/user-attachments/assets/f1129d06-12de-4fed-a8ed-34f76a947ede"> icon on right vertical bar
- After that go to analytical tab and select all the bands with image format as tiff 32 bit , high resolution , wgs1984 format and all bands checkd

<img width="1255" alt="image" src="https://github.com/user-attachments/assets/2d5d8318-2b71-4daa-b720-8fa046e31f58">

You can also download pregenerated indices such as NDVI , False color tiff only or specific bands whichever best suits your need . We are downloading all the bands as we wanna do the processing by ourselves
- Click download


<img width="1256" alt="image" src="https://github.com/user-attachments/assets/d73cfa52-4757-4ca8-9460-d2c0f7dca6ba">

## Preprocess

We get all the bands as separate tiff from the sentinel as we downloaded raw format 

<img width="973" alt="image" src="https://github.com/user-attachments/assets/d47534e4-4bb4-4331-9faf-de9a5c8c30de">

- lets create a composite image : 

This can be done through GIS tools or gdal 

1. **Using [gdal_merge](https://gdal.org/programs/gdal_merge.html)**:

We need to rename the downloaded file to band1,band2 like this to avoid slashes in the filename 
Lets process upto band 9 for this exercise , you can choose the band as your requirement
```shell
gdal_merge.py -separate -o sentinel2_composite.tif band1.tif band2.tif band3.tif band4.tif band5.tif band6.tif band7.tif band8.tif band9.tif 
```

2. **Using QGIS** : 
- Load all individual bands to QGIS 
- Go to Raster > Miscellanaeous > Merge

<img width="582" alt="image" src="https://github.com/user-attachments/assets/579deffc-b5c7-4df0-b28f-79e27b7e4479">

- While merging you need to make sure you check 'place each input file in sep band'

<img width="683" alt="image" src="https://github.com/user-attachments/assets/3baf23a5-54c5-48da-a185-622139baf2b1">

- Now export your merged tiff to raw geotiff as composite

- Make sure your image is in WGS1984
  in our case image is already is in ws1984 so no need for the conversion 
- Make sure you don't have any nodata if yes fill them with 0
  ```shell
  gdalwarp -overwrite -dstnodata 0 "$input_file" "${output_file}_nodata.tif"
  ```
- Finally make sure your ouput image is in COG
  ```shell
  gdal_translate -of COG "$input_file" "$output_file"
  ```

I am using the [bash script](https://github.com/kshitijrajsharma/cog2h3/blob/main/pre.sh) provided in cog2he library to automate those 

```shell
sudo bash pre.sh sentinel2_composite.tif
```

## Process and creation of h3 cells
Now finally as we have done the preprocessing script , lets move forward to compute h3 cells for each bands in the composite cog image 

- Install cog2h3
  ```shell
  pip install cog2h3
  ```
- Export you database credentials
  ```shell
  export DATABASE_URL="postgresql://user:password@host:port/database"
  ```
- Run
  We are using resolution 10 for this sentinel image, however you will also see in the script itself which will print the optimal resolution for your raster that makes the h3 cell smaller than your smallest of pixel in raster.
  ```shell
  cog2h3 --cog sentinel2_composite_preprocessed.tif --table sentinel --multiband --res 10
  ```
It took a minute for us to compute and store result in postgresql 

Logs : 
```log
2024-08-24 08:39:43,233 - INFO - Starting processing
2024-08-24 08:39:43,234 - INFO - COG file already exists at sentinel2_composite_preprocessed.tif
2024-08-24 08:39:43,234 - INFO - Processing raster file: sentinel2_composite_preprocessed.tif
2024-08-24 08:39:43,864 - INFO - Determined Min fitting H3 resolution for band 1: 11
2024-08-24 08:39:43,865 - INFO - Resampling original raster to: 200.786148m
2024-08-24 08:39:44,037 - INFO - Resampling Done for band 1
2024-08-24 08:39:44,037 - INFO - New Native H3 resolution for band 1: 10
2024-08-24 08:39:44,738 - INFO - Calculation done for res:10 band:1
2024-08-24 08:39:44,749 - INFO - Determined Min fitting H3 resolution for band 2: 11
2024-08-24 08:39:44,749 - INFO - Resampling original raster to: 200.786148m
2024-08-24 08:39:44,757 - INFO - Resampling Done for band 2
2024-08-24 08:39:44,757 - INFO - New Native H3 resolution for band 2: 10
2024-08-24 08:39:45,359 - INFO - Calculation done for res:10 band:2
2024-08-24 08:39:45,366 - INFO - Determined Min fitting H3 resolution for band 3: 11
2024-08-24 08:39:45,366 - INFO - Resampling original raster to: 200.786148m
2024-08-24 08:39:45,374 - INFO - Resampling Done for band 3
2024-08-24 08:39:45,374 - INFO - New Native H3 resolution for band 3: 10
2024-08-24 08:39:45,986 - INFO - Calculation done for res:10 band:3
2024-08-24 08:39:45,994 - INFO - Determined Min fitting H3 resolution for band 4: 11
2024-08-24 08:39:45,994 - INFO - Resampling original raster to: 200.786148m
2024-08-24 08:39:46,003 - INFO - Resampling Done for band 4
2024-08-24 08:39:46,003 - INFO - New Native H3 resolution for band 4: 10
2024-08-24 08:39:46,605 - INFO - Calculation done for res:10 band:4
2024-08-24 08:39:46,612 - INFO - Determined Min fitting H3 resolution for band 5: 11
2024-08-24 08:39:46,612 - INFO - Resampling original raster to: 200.786148m
2024-08-24 08:39:46,619 - INFO - Resampling Done for band 5
2024-08-24 08:39:46,619 - INFO - New Native H3 resolution for band 5: 10
2024-08-24 08:39:47,223 - INFO - Calculation done for res:10 band:5
2024-08-24 08:39:47,230 - INFO - Determined Min fitting H3 resolution for band 6: 11
2024-08-24 08:39:47,230 - INFO - Resampling original raster to: 200.786148m
2024-08-24 08:39:47,239 - INFO - Resampling Done for band 6
2024-08-24 08:39:47,239 - INFO - New Native H3 resolution for band 6: 10
2024-08-24 08:39:47,829 - INFO - Calculation done for res:10 band:6
2024-08-24 08:39:47,837 - INFO - Determined Min fitting H3 resolution for band 7: 11
2024-08-24 08:39:47,837 - INFO - Resampling original raster to: 200.786148m
2024-08-24 08:39:47,845 - INFO - Resampling Done for band 7
2024-08-24 08:39:47,845 - INFO - New Native H3 resolution for band 7: 10
2024-08-24 08:39:48,445 - INFO - Calculation done for res:10 band:7
2024-08-24 08:39:48,453 - INFO - Determined Min fitting H3 resolution for band 8: 11
2024-08-24 08:39:48,453 - INFO - Resampling original raster to: 200.786148m
2024-08-24 08:39:48,461 - INFO - Resampling Done for band 8
2024-08-24 08:39:48,461 - INFO - New Native H3 resolution for band 8: 10
2024-08-24 08:39:49,046 - INFO - Calculation done for res:10 band:8
2024-08-24 08:39:49,054 - INFO - Determined Min fitting H3 resolution for band 9: 11
2024-08-24 08:39:49,054 - INFO - Resampling original raster to: 200.786148m
2024-08-24 08:39:49,062 - INFO - Resampling Done for band 9
2024-08-24 08:39:49,063 - INFO - New Native H3 resolution for band 9: 10
2024-08-24 08:39:49,647 - INFO - Calculation done for res:10 band:9
2024-08-24 08:39:51,435 - INFO - Converting H3 indices to hex strings
2024-08-24 08:39:51,906 - INFO - Overall raster calculation done in 8 seconds
2024-08-24 08:39:51,906 - INFO - Creating or replacing table sentinel in database
2024-08-24 08:40:03,153 - INFO - Table sentinel created or updated successfully in 11.25 seconds.
2024-08-24 08:40:03,360 - INFO - Processing completed
```

## Analyze 

Since now we have our data in postgresql , Lets do some analysis 

- Verify we have all the bands we processed ( Remember we processed from band 1 to 9 )

```sql
select *
from sentinel
```

<img width="1024" alt="image" src="https://github.com/user-attachments/assets/390e612e-cf2e-4402-b745-27a3ba3578ac">

- Compute ndvi for each cell
```sql
explain analyze 
select h3_ix , (band8-band4)/(band8+band4) as ndvi
from public.sentinel
```
Query Plan : 

```log
QUERY PLAN                                                                                                       |
-----------------------------------------------------------------------------------------------------------------+
Seq Scan on sentinel  (cost=0.00..28475.41 rows=923509 width=16) (actual time=0.014..155.049 rows=923509 loops=1)|
Planning Time: 0.080 ms                                                                                          |
Execution Time: 183.764 ms                                                                                       |
```
As you can see here for all the rows in that area the calculation is instant . This is true for all other indices and you can compute complex indices join with other tables using the h3_ix primary key and derive meaningful result out of it without worrying as postgresql is capable of handling complex queries and table join.

## Visualize and verification 
Lets visualize and verify if the computed indices are true 

- Create table ( for visualizing in QGIS ) 
```sql
create table ndvi_sentinel
as(
select h3_ix , (band8-band4)/(band8+band4) as ndvi
from public.sentinel )
```
- Lets add geometry to visualize the h3 cells
This is only necessary to visualize in QGIS , if you build an [minimal API](https://github.com/kshitijrajsharma/minimal-h3-mvt-with-fastapi) by yourself you don't need this as you can construct geometry directly from query 
```sql
ALTER TABLE ndvi_sentinel  
ADD COLUMN geometry geometry(Polygon, 4326) 
GENERATED ALWAYS AS (h3_cell_to_boundary_geometry(h3_ix)) STORED;
```

- Create index on geometry 
```sql
create index on ndvi_sentinel(geometry);
```
- Connect your database in QGIS and visualize the table on the basis of ndvi value
Lets get the area near Fewa lake or cloud

<img width="1115" alt="image" src="https://github.com/user-attachments/assets/e5ec71b9-d56b-4d93-9ad7-ba9b431bbe70">

As we know value between -1.0 to 0.1 should represent Deep water or dense clouds
lets see if thats true ( making first category as transparent to see the underlying image ) 
- Check clouds : 

<img width="979" alt="image" src="https://github.com/user-attachments/assets/d9c4cd44-4526-4a79-9e2c-cb3f8c70c515">
- Check Lake 

<img width="897" alt="image" src="https://github.com/user-attachments/assets/f12bebed-69a8-44ee-aee7-5f36838f53df">
 As there were clouds around the lake hence nearby fields are covered by cloud which makes sense

<img width="409" alt="image" src="https://github.com/user-attachments/assets/4d06b61f-5648-4c78-9655-82f41304faf7">

 Thank you for reading ! See you in next blog
