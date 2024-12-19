import requests
import os
import logging
import streamlit as st
import uuid
import io
from io import BytesIO
import json
# import base64
# from time import sleep

from PIL import Image
from azure.storage.queue import QueueServiceClient
from azure.storage.blob import BlobServiceClient

#from image_utils import to_40x20_binary, serialize_grayscale

# Set the logging level for this script
logging.basicConfig(level=logging.INFO)

# Set the logging level for all azure-* libraries
azure_logger = logging.getLogger('azure')
azure_logger.setLevel(logging.WARNING)

# Decide if we're running in the cloud or locally
CLOUD = os.environ.get("USE_AZURE_CREDENTIAL", "false").lower() == "true"

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


URL = os.environ["PREDICT_FLOWER_URL"]

def call_predict(image_file) -> dict|None:
    # POST request to api with image file included
    try:
        files = {"image_file": (image_file.name, image_file, "image/jpeg")}
        response = requests.post(URL, files=files)

    except requests.exceptions.ConnectionError as e:
        st.warning("Failed to connect to the backend.")
        return None

    # Handle response
    if response.ok:
        st.write("Prediction: ", response.json())
    else:
        st.warning("Failed to get prediction from the backend.")
        st.write(response.text)
        return None

    return response.json()

## UI STARTS: ##
st.title("Upload a picture and predict its species")

st.write("")

image_file = st.file_uploader("Upload picture for prediction (.JPEG files only)", type=["jpg","jpeg"])

# Ask user to predict the image using REST API backend model
if image_file is not None: # if image_file is not None:
    logging.info(f"Loaded image_file type1: {type(image_file)}")
    logging.info(f"Loaded image_file name: {image_file.name}")

    st.image(image_file, "Uploaded image")

    if st.button("Predict"):

        predict_json = call_predict(image_file)

    st.write("Not happy with the prediction? Submit the drawing with a label so that we can improve the model.")
    logging.info(f"image_file type2: {type(image_file)}")

    flower_list = ["dandelion", "daisy", "tulips", "sunflowers", "roses"]
    label = st.selectbox("Label:", flower_list, placeholder="Select correct label")
    flower_index = flower_list.index(label)

    if st.button("Send picture to training"):

        # upload picture as a blob: https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-upload-python

        with get_blob_service_client() as blob_service_client:
            # Python unique file name: https://stackoverflow.com/questions/2961509/python-how-to-create-a-unique-file-name
            image_name = f"{uuid.uuid4()}_{image_file.name}"

            container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
            blob_client = container_client.get_blob_client(image_name)

            with io.BytesIO(image_file.getvalue()) as uploaded_file:
                blob_client.upload_blob(uploaded_file.read(), overwrite=True)

            logging.info(f"blob_file {image_name} uploaded into blob storage.")

        # Lets send image info into the queue.
        with get_queue_service_client() as queue_service_client:
            # upload queue client.
            with queue_service_client.get_queue_client(os.environ["STORAGE_QUEUE"]) as queue_client:
                logging.info(f"image_file type3: {type(image_file)}")
                logging.info(f"flower_index type: {type(flower_index)}")
                logging.info(f"flower_index: {flower_index}")

                # message in .json format.
                message = {
                    "image_name": image_name,
                    "label": flower_index
                    }

                queue_client.send_message(json.dumps(message)) # sends image_name and flower label into queue as a message
                json_dump = json.dumps(message)

                logging.info(json_dump)
                logging.info(message)
                logging.info(f"Message ({image_name}) as ({label}) sent to Queue ({os.environ['STORAGE_QUEUE']})")

                st.write(f"Sent: {image_name} as label {flower_list[flower_index]} to model training ({os.environ['STORAGE_QUEUE']}).")
                st.write("You can now upload a new picture.")


                # ## Just a test to load picture from queue, did not work...##
                # https://github.com/Azure/azure-sdk-for-python/issues/11784
                # https://learn.microsoft.com/en-us/azure/storage/queues/storage-queues-introduction
                # https://learn.microsoft.com/en-us/answers/questions/905848/storage-queue-message-size-limit
                # # load image from queue as a message.
                # messages = queue_client.receive_messages(messages_per_page=1)
                # logging.info(type(messages))

                # for msg in messages:
                #     logging.info(type(msg))
                #     content = msg.content  # This should get the base64 encoded message
                #     logging.info(type(content))
                #     queue_client.delete_message(msg)  # delete the msg.
                #     if content:
                #         # Decode
                #         image_bytes = BytesIO(base64.b64decode(content))
                #         logging.info(len(image_bytes))
                #         # back to image
                #         image = Image.open(image_bytes)
                #     st.image(image, caption="Image from Azure Queue", use_column_width=True)
                # else:
                #     st.write("didnt receive message/picture :(")
                
                # content = get_message_from_queue(queue_name, connection_string)
                # if content:
                #     # Decode the base64 content
                #     image_bytes = BytesIO(base64.b64decode(content))
                #     image = Image.open(image_bytes)
    
                #     # Display the image in Streamlit
                # st.image(image, caption="Image from Azure Queue", use_column_width=True)

# def upload(model_file, file_path):
#     """Append new model to models.
#     """
#     logging.info(f"Uploading model to storage container.")
#     logging.info(f"model_file: {model_file}")
#     logging.info(f"file_path: {file_path}")
#     with get_blob_service_client() as blob_service_client:
#         container_client = blob_service_client.get_container_client(os.environ["STORAGE_CONTAINER"])
#         with open(model_file, "rb") as data:
#             blob_client = container_client.get_blob_client(file_path)
#             blob_client.upload_blob(data, overwrite=True)
#             logging.info(f"Upload complete for {model_file}.")