import joblib
import os
import logging
import tempfile
import tensorflow as tf
from io import BytesIO
from keras.preprocessing import image

from fastapi import FastAPI, UploadFile, File, HTTPException
from datetime import datetime
#from sklearn.linear_model import LogisticRegression

from models import Prediction
from utils import latest_model_version, load_model # deserialize_grayscale

def format_image(image):
    image = tf.image.resize(image, (224, 224))/ 255.0
    return image

# Set the logging level for this script
logging.basicConfig(level=logging.INFO)

# Set the logging level for all azure-* libraries
azure_logger = logging.getLogger('azure')
azure_logger.setLevel(logging.WARNING)


## Lets build the predict API
app = FastAPI()


@app.post("/predict")
def predict_hello(image_file:   UploadFile = File(...)) -> Prediction:

    # lets make sure that the image is correct file type.
    if image_file.content_type not in ("image/jpg", "image/jpeg"):
        raise HTTPException(status_code=400, detail="Only JPG and JPEG files are predictable.")
    
    # bring latest model info and bytes
    latest_version = latest_model_version()
    logging.info(latest_version)
    model_bytes = load_model(latest_version) 
    logging.info("did it work? Yes")
    
    #bytes into path, wont be deleting temp file.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".keras") as temp_file:
        temp_file.write(model_bytes) # model bytes to tempfile.
        temp_file_path = temp_file.name

    # load the model
    model = tf.keras.models.load_model(temp_file_path)
    logging.info(f"model: {model.summary(show_trainable=True)}")

    image_bytes = image_file.file.read()
    test_image = image.load_img(BytesIO(image_bytes))
    test_image = format_image(test_image)

    output = model.predict(tf.expand_dims(test_image, axis=0), batch_size=1)
    logging.info(output)

    output = tf.nn.softmax(output)
    logging.info(f"Output: {output}")
    output_index = tf.argmax(output, axis=1)
    confidence = float(output[0][int(output_index)])
    logging.info(f"Confidence: {confidence}")
    flower_list = ["dandelion", "daisy", "tulips", "sunflowers", "roses"]
    prediction = flower_list[int(output_index)]
    logging.info(f"Prediction: {prediction}")

    return Prediction(
        label=output_index,
        confidence=confidence,
        prediction=prediction,
        version=latest_version,
        version_iso=datetime.fromtimestamp(latest_version).isoformat()
    )
