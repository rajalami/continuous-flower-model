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
    logging.info("did it work? NO")
    
    #bytes into path, wont be deleting temp file.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".keras") as temp_file:
        temp_file.write(model_bytes) # model bytes to tempfile.
        temp_file_path = temp_file.name

    # load the model
    model = tf.keras.models.load_model(temp_file_path)
    logging.info(f"model: {model.summary(show_trainable=True)}")

    image_bytes = image_file.file.read()
    logging.info(f"image_bytes read{image_bytes}")
    test_image = image.load_img(BytesIO(image_bytes))
    logging.info(f"image_bytes read{image_bytes}")
    test_image = format_image(test_image)

    output = model.predict(tf.expand_dims(test_image, axis=0), batch_size=1)

    predicted_class = tf.argmax(output, axis=1).numpy()[0]  # Get the index of the highest probability
    logging.info(f"Index of predicted class: {predicted_class}")
    flower_list = ["dandelion", "daisy", "tulips", "sunflowers", "roses"]
    prediction = flower_list[predicted_class]
    logging.info(f"Predicted class label: {prediction}")
    confidence_score = tf.reduce_max(tf.nn.softmax(output)).numpy()[0]  # Get the confidence score
    logging.info(f"Confidence_score: {confidence_score}")

    # logging.info(f"Prediction: {predicted_class}")

    return Prediction(
        label=predicted_class,
        confidence=confidence_score,
        prediction=prediction,
        version=latest_version,
        version_iso=datetime.fromtimestamp(latest_version).isoformat()
    )
