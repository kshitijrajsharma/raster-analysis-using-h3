## Copyright @ Kshitij Raj Sharma 2024
## Note : Input cog should be in wgs 1984 if not reproject the raster

## Convert your tiff to cog using gdal (https://gdal.org/drivers/raster/cog.html#raster-cog)
# gdal_translate -of COG input.tif output_cog.tif

## Install
# pip install h3 h3ronpy rasterio asyncio asyncpg

## Usage
# python cog2h3.py --cog /static/my-cog.tif --table cog_h3 --res 8

import argparse
import asyncio
import logging
import os
import time

import aiohttp
import asyncpg
import h3
import numpy as np
import pyarrow as pa
import rasterio
from h3ronpy.arrow.raster import nearest_h3_resolution, raster_to_dataframe
from rasterio.enums import Resampling

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)
## setup static dir for cog
STATIC_DIR = os.getenv("STATIC_DIR", "static")
os.makedirs(STATIC_DIR, exist_ok=True)


async def download_cog(cog_url: str) -> str:
    """Downloads COG to file dir if not exists

    Args:
        cog_url (str): where to download cog from ?

    Raises:
        Exception: _description_

    Returns:
        str: file path of downloaded url
    """
    cog_file_name = os.path.basename(cog_url)
    file_path = os.path.join(STATIC_DIR, cog_file_name)

    if os.path.exists(file_path):
        logging.info(f"COG file already exists: {file_path}")
        return file_path

    logging.info(f"Downloading COG from {cog_url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(cog_url) as response:
            if response.status != 200:
                logging.error(f"Failed to download COG from {cog_url}")
                raise Exception(f"Failed to download COG from {cog_url}")
            with open(file_path, "wb") as tmp_file:
                tmp_file.write(await response.read())
                logging.info(f"Downloaded COG to {file_path}")
                return file_path


async def create_or_replace_table_arrow(table: pa.Table, table_name: str, db_url: str):
    """Inserts vector h3 data to database"""
    logging.info(f"Creating or replacing table {table_name} in database")
    start_time = time.time()

    conn = await asyncpg.connect(dsn=db_url)

    await conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    await conn.execute(
        f"""
        CREATE TABLE {table_name} (
            h3_ix h3index PRIMARY KEY,
            cell_value FLOAT
        )
    """
    )

    h3_index_column = table.column("h3_ix").chunks
    value_column = table.column("value").chunks

    for h3_chunk, value_chunk in zip(h3_index_column, value_column):
        h3_indexes = list(zip(h3_chunk.to_pylist(), value_chunk.to_pylist()))
        await conn.executemany(
            f"INSERT INTO {table_name} (h3_ix, cell_value) VALUES ($1, $2)", h3_indexes
        )

    await conn.close()

    end_time = time.time()
    logging.info(
        f"Table {table_name} created or updated successfully in {end_time - start_time:.2f} seconds."
    )


def convert_h3_indices_arrow(table: pa.Table) -> pa.Table:
    """Convert h3 python inter uint8 indices to hex strings"""

    logging.info("Converting H3 indices to hex strings")

    h3_indices_column = table.column("cell")

    converted_chunks = [
        pa.array([h3.h3_to_string(x) for x in chunk.to_pylist()])
        for chunk in h3_indices_column.chunks
    ]

    new_columns = table.remove_column(table.schema.get_field_index("cell"))
    new_columns = new_columns.append_column("h3_ix", pa.chunked_array(converted_chunks))

    return new_columns


def get_edge_length(res, unit="km"):
    """Gets edge length of constant h3 cells using resolution"""

    edge_lengths_km = [
        1281.256011,
        483.0568391,
        182.5129565,
        68.97922179,
        26.07175968,
        9.854090990,
        3.724532667,
        1.406475763,
        0.531414010,
        0.200786148,
        0.075863783,
        0.028663897,
        0.010830188,
        0.004092010,
        0.001546100,
        0.000584169,
    ]

    if res < 0 or res >= len(edge_lengths_km):
        raise ValueError("Invalid resolution. It should be between 0 and 15.")

    edge_length_km = edge_lengths_km[res]

    if unit == "km":
        return edge_length_km
    elif unit == "m":
        return edge_length_km * 1000
    else:
        raise ValueError("Invalid unit. Use 'km' for kilometers or 'm' for meters.")


async def process_raster(cog_url: str, table_name: str, h3_res):
    """Resamples and generates h3 value for raster"""
    cog_file_path = await download_cog(cog_url)
    raster_time = time.time()

    logging.info(f"Processing raster file: {cog_file_path}")
    with rasterio.open(cog_file_path) as src:
        grayscale = src.read(1)
        transform = src.transform
        # profile = src.profile.copy()

        native_h3_res = nearest_h3_resolution(
            grayscale.shape, src.transform, search_mode="smaller_than_pixel"
        )
        logging.info(f"Determined Min fitting H3 resolution: {native_h3_res}")

        if h3_res < native_h3_res:
            ### if required h3 resolution is smaller than native h3 , lets resample the raster to smaller which will avoid aggregation in vector analysis and would be faster + efficient
            logging.info(
                f"Resampling original raster to : {get_edge_length(h3_res-1, unit='m')}m"
            )

            scale_factor = src.res[0] / (get_edge_length(h3_res - 1, unit="m") / 111320)
            data = src.read(
                out_shape=(
                    src.count,
                    int(src.height * scale_factor),
                    int(src.width * scale_factor),
                ),
                resampling=Resampling.nearest,
            )
            transform = src.transform * src.transform.scale(
                (src.width / data.shape[-1]), (src.height / data.shape[-2])
            )

            grayscale = data[0]
            logging.info("Resampling Done")
            nodata_value = src.nodata
            if (
                nodata_value is not None
            ):  # Replace nodata value to 0 ( avoids unusual color numbers in h3 cells)
                grayscale = np.where(grayscale == nodata_value, 0, grayscale)

            native_h3_res = nearest_h3_resolution(
                grayscale.shape, transform, search_mode="smaller_than_pixel"
            )
            ### native resolution should match the desired resolution now
            logging.info(f"New Native H3 resolution: {native_h3_res}")

            ### uncomment this if you need new profile and to save the resampled dataset
            # profile.update(
            #     {
            #         "height": data.shape[-2],
            #         "width": data.shape[-1],
            #         "transform": transform,
            #     }
            # )
        ## get h3 cell value from raster
        grayscale_h3_df = raster_to_dataframe(
            grayscale,
            transform,
            native_h3_res,
            nodata_value=None,
            compact=True,
        )
        ## now convert these uint8 value to h3 hex strings
        grayscale_h3_df = convert_h3_indices_arrow(grayscale_h3_df)
        logging.info(
            f"Raster calculation done in {int(time.time()-raster_time)} seconds"
        )
        await create_or_replace_table_arrow(grayscale_h3_df, table_name, DATABASE_URL)

    # with rasterio.open("resampled.tif", "w", **profile) as dataset:
    #     dataset.write(data)


def main():
    """Iron Man Main function"""
    parser = argparse.ArgumentParser(
        description="Process a Cloud Optimized GeoTIFF and upload data to PostgreSQL."
    )
    parser.add_argument(
        "--cog",
        type=str,
        required=True,
        help="URL of the Cloud Optimized GeoTIFF",  ### IMP : This should be in wgs84
    )
    parser.add_argument(
        "--table", type=str, required=True, help="Name of the database table"
    )
    parser.add_argument("--res", type=int, help="H3 resolution level")

    args = parser.parse_args()

    logging.info("Starting processing")
    asyncio.run(process_raster(args.cog, args.table, args.res))
    logging.info("Processing completed")


if __name__ == "__main__":
    main()
