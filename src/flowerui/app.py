import requests
import os
import logging
import streamlit as st

from PIL import Image
from azure.storage.queue import QueueServiceClient

#from image_utils import to_40x20_binary, serialize_grayscale

# Set the logging level for this script
logging.basicConfig(level=logging.INFO)

# Set the logging level for all azure-* libraries
azure_logger = logging.getLogger('azure')
azure_logger.setLevel(logging.WARNING)

# Decide if we're running in the cloud or locally
CLOUD = os.environ.get("USE_AZURE_CREDENTIAL", "false").lower() == "true"

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

### UI STARTS: ###
st.title("Upload a picture and predict its species")

st.write("")


image_file = st.file_uploader("Upload picture for prediction (.JPEG files only)", type=["jpg","jpeg"])


# Ask user to predict the image using REST API backend model
if image_file is not None: # if image_file is not None:

    st.image(image_file, "Uploaded image")
    #st.write(f"Uploaded file name: {image_file.name}")
    if st.button("Predict"):

        predict_json = call_predict(image_file)

    st.write("Not happy with the prediction? Submit the drawing with a label so that we can improve the model.")

    flower_list = ["dandelion", "daisy", "tulips", "sunflowers", "roses"]
    label = st.selectbox("Label:", flower_list, placeholder="Select correct label")
    flower_index = flower_list.index(label)

    if st.button("Train a new model"):

        with get_queue_service_client() as queue_service_client:
            with queue_service_client.get_queue_client(os.environ["STORAGE_QUEUE"]) as queue_client:
                compressed_b64 = (image_file, flower_index)
                queue_client.send_message(compressed_b64)

                logging.info(f"Message ({label}) as ({compressed_b64}) sent to Queue ({os.environ['STORAGE_QUEUE']})")
                st.write(f"Sent: IMAGE #{compressed_b64}# as label {flower_list[flower_index]} sen to model training queue. \n You can now upload a new picture.")


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