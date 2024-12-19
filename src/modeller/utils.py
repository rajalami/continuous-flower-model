import os
import logging
import zlib
import numpy as np
import pandas as pd
from functools import lru_cache
import json
import tensorflow as tf
import keras
from datetime import datetime
import pathlib
import zipfile

from base64 import b64decode
from io import StringIO, BytesIO
from PIL import Image
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient
from sklearn.linear_model import LogisticRegression

# Are we running in the cloud?
CLOUD = os.environ.get("USE_AZURE_CREDENTIAL", "false").lower() == "true"

def format_image(image):
    image_res = 224
    formated_image = tf.image.resize(image, (image_res, image_res))
    return formated_image

def get_blob_service_client():
    """
    The STORAGE_CONNECTION_STRING is only set up when running in the cloud. 
    If it's not set, we're running locally with Azurite.
    """
    if CLOUD:
        from azure.identity import DefaultAzureCredential # type: ignore
        credential = DefaultAzureCredential()
        account_url = os.environ["STORAGE_BLOB_URL"]
        return BlobServiceClient(account_url=account_url, credential=credential)
    else:
        return BlobServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
    
def get_queue_service_client():
    """
    The STORAGE_CONNECTION_STRING is only set up when running in the cloud. 
    If it's not set, we're running locally with Azurite.
    """
    if CLOUD:
        from azure.identity import DefaultAzureCredential # type: ignore
        credential = DefaultAzureCredential()
        account_url = os.environ["STORAGE_QUEUE_URL"]
        return QueueServiceClient(account_url=account_url, credential=credential)
    else:
        return QueueServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
    
# Check how many messages are in the queue
def n_images_waiting() -> int:
    with get_queue_service_client() as queue_client:
        queue = queue_client.get_queue_client(os.environ["STORAGE_QUEUE"])
        queue_properties = queue.get_queue_properties()
        message_count = queue_properties.approximate_message_count
        logging.info(f"Labeled images waiting in queue: {message_count}")
        return message_count

def get_all_from_queue(): #-> list[tuple[image, int]]:
    """
    checks queue for messages and loads image counterparts from blob_storage.
    """
    logging.info("Getting all images from the queue.")

    with get_queue_service_client() as queue_service_client:
        queue = queue_service_client.get_queue_client(os.environ["STORAGE_QUEUE"])
        messages = queue.receive_messages(messages_per_page=32)
        new_rows = []

        for msg in messages:
            
            # https://stackoverflow.com/questions/39491420/python-jsonexpecting-property-name-enclosed-in-double-quotes?page=2&tab=scoredesc#tab-top
            message_content = json.loads(msg.content)
            image_name = message_content.get("image_name")
            label = message_content.get("label")
            logging.info(f"image_name: {image_name}")
            logging.info(f"label: {label}")
            
            # load images from blob storage.
            with get_blob_service_client() as blob_service_client:
                container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
                blob_client = container_client.get_blob_client(image_name)
                
                blob_data = blob_client.download_blob()
                bytes = blob_data.readall()
                logging.info(f"Bytes length: {len(bytes)}")
                image = keras.preprocessing.image.load_img(BytesIO(bytes))

                # format image to fit for training
                image = format_image(image)
                logging.info(f"Image type: {type(image)}")

                # delete blob
                blob_client.delete_blob()
            
            # pair the image and label to training data list
            new_rows.append((image, label))
            # delete message from queue
            queue.delete_message(msg)

        logging.info(f"Got {len(new_rows)} images from the queue.")
        return new_rows

def train_model(dataset: str, model_version: int) -> LogisticRegression:
    """Train a model on the given dataset.
    """
    logging.info(f"Training the model on {len(dataset.splitlines())} samples.")
    df = pd.read_csv(StringIO(dataset), header=None)
    logging.info(f"Loaded {len(df)} samples from the dataset.")
    logging.info(f"Last row: {df.iloc[-1]}")
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]
    model = LogisticRegression()
    model.fit(X, y)

    return model

def latest_model_version() -> int:
    """
    returns the value of latest saved model from blob storage
    used to load newest model for prediction.
    """
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
        blobs = container_client.list_blobs(name_starts_with="models/")

        latest = max([int(x.name.split("_")[1].split(".")[0]) for x in blobs])

        unix_to_iso = datetime.fromtimestamp(latest).isoformat()
        logging.info(f"Latest_model_version() seeing: {latest} created at {unix_to_iso}")
        return latest
    
@lru_cache(maxsize=5)
def load_model(version:int):
    # Find the latest model from /models folder in the storage container
    # The model name follows the pattern model_{unix_seconds}.keras
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
        blob_client = container_client.get_blob_client(f"models/flowersmodel_{version}.keras") 
        logging.info(f"Loading model version {version}.")
        logging.info(f"type {type(blob_client)}.")

        blob_data = blob_client.download_blob()
        file_bytes = blob_data.readall()
        logging.info(f"Downloaded model size: {len(file_bytes)} bytes.")
        logging.info(f"type {type(file_bytes)}.")
        return file_bytes

        # https://stackoverflow.com/questions/74693871/why-joblib-is-not-recommended-when-saving-keras-model
        # with BytesIO() as data:
        #     logging.info(f"1")
        #     logging.info(f"{data}")
        #     blob_client.download_blob().readinto(data)
        #     logging.info(f"{data}")
        #     logging.info(f"2")
        #     return joblib.load(data)

def load_dataset():
    """
    unzips the data.
    """
    logging.info(f"Loading validation dataset.")
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
        blob_client = container_client.get_blob_client("datasets/val_data.zip")

        os.makedirs("./val/", exist_ok=True)
        target_folder = pathlib.Path("./val/")
        blob_stream = blob_client.download_blob()
        zip_data = blob_stream.readall()

        with zipfile.ZipFile(BytesIO(zip_data), mode="r") as archive:
            archive.extractall(target_folder)

        return None


### UNUSED

def upload(csv_data:str, file_path:str):
    """Append the new data to the dataset.
    """
    logging.info("Uploading {type(csv_data)} to {file_path}.")
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
        blob_client = container_client.get_blob_client(file_path)
        blob_client.upload_blob(csv_data, overwrite=True)
        logging.info(f"Upload complete for {file_path}.")

def images_to_csv(images: list[tuple[Image.Image, int]]) -> str:
    """Convert a list of images to a CSV string.
    """
    new_rows = []
    for img, label in images:
        # Convert the image to a binary string
        pixel_data = [str(int(x / 255)) for x in img.getdata()]
        pixel_csv = ",".join(pixel_data)
        new_rows.append(f"{pixel_csv},{label}")
    logging.info(f"The first incoming row: {new_rows[0][:25]}...")
    
    # Convert to a single newline-separated string
    new_rows = "\n".join(new_rows) + "\n"
    return new_rows

def upload_model(model_file, file_path):
    """
    Append new model to models.
    """
    logging.info(f"Uploading model to storage container.")
    logging.info(f"model_file: {model_file}")
    logging.info(f"file_path: {file_path}")
    with get_blob_service_client() as blob_service_client:
        container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
        with open(model_file, "rb") as data:
            blob_client = container_client.get_blob_client(file_path)
            blob_client.upload_blob(data, overwrite=True)
            logging.info(f"Upload complete for {model_file}.")