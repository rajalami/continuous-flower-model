import requests
import os
import logging
import streamlit as st

from PIL import Image
from streamlit_drawable_canvas import st_canvas
from azure.storage.queue import QueueServiceClient

from image_utils import to_40x20_binary, serialize_grayscale

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


# Drawing parameters
drawing_mode = "freedraw"
stroke_width = st.sidebar.slider("Stroke width: ", 5, 25, 5)
stroke_color = "#000" #black

# Create a canvas component
canvas_result = st_canvas(
    stroke_width=stroke_width,
    stroke_color=stroke_color,
    background_color="#FFF",
    width=400,
    height=200,
    drawing_mode=drawing_mode,
    key="canvas",
)

URL = os.environ["PREDICT_HELLO_URL"]

def call_predict(image) -> dict|None:
    try:
        response = requests.post(URL, json={"image": serialize_grayscale(image)})
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


# Ask user to predict the image using REST API backend model
if canvas_result.image_data is not None:

    if st.button("Predict"):   
        img = Image.fromarray(canvas_result.image_data)

        # # Process the image to 40x20 black and white (0 or 1)
        img = to_40x20_binary(img)
        
        predict_json = call_predict(img)

    st.write("Not happy with the prediction? Submit the drawing with a label so that we can improve the model.")

    label = st.selectbox("Label: ", ["hello", "world"])

    if st.button("Submit for training"):
        img = Image.fromarray(canvas_result.image_data)
        img = to_40x20_binary(img)

        label_int = 1 if label == "hello" else 0

        with get_queue_service_client() as queue_service_client:
            with queue_service_client.get_queue_client(os.environ["STORAGE_QUEUE"]) as queue_client:
                compressed_b64 = serialize_grayscale(img, label=label_int)
                queue_client.send_message(compressed_b64)

                logging.info(f"Message ({label}) as ({compressed_b64}) sent to Queue ({os.environ['STORAGE_QUEUE']})")
                st.write(f"Sent: {compressed_b64} as {label_int} (hello=1, world=0)")
