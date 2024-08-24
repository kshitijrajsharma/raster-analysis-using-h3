## Process multiband rasters (Sentinel-2) with h3 index and create indices 

Hi, In this blog we will talk about how we can process multiband raster and create indices with ease. We will be using sentinel-2 image and create NDVI from the processed h3 cells and visualize the results

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

Now lets merge the image

This can be done through GIS tools or gdal 

Using QGIS : 
- Load all individual bands to QGIS 
- Go to Raster > Miscellanaeous > Merge
<img width="582" alt="image" src="https://github.com/user-attachments/assets/579deffc-b5c7-4df0-b28f-79e27b7e4479">
- While merging you need to make sure you check 'place each input file in sep band'
<img width="683" alt="image" src="https://github.com/user-attachments/assets/3baf23a5-54c5-48da-a185-622139baf2b1">
- Now export your merged tiff to raw geotiff as composite


