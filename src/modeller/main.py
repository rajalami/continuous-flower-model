import joblib
import time
import logging
import time
import tempfile
import tensorflow as tf
import keras
import os

from datetime import datetime
from io import BytesIO

from utils import (
    n_images_waiting,
    load_dataset,
    get_all_from_queue,
    upload_model,
    latest_model_version,
    load_model
)

# Set the logging level for this script
logging.basicConfig(level=logging.INFO)

# Set the logging level for all azure-* libraries
azure_logger = logging.getLogger("azure")
azure_logger.setLevel(logging.WARNING)

load_dataset()

#["dandelion", "daisy", "tulips", "sunflowers", "roses"]
os.rename("./val/dandelion", "./val/0_dandelion")
os.rename("./val/daisy", "./val/1_daisy")
os.rename("./val/tulips", "./val/2_tulips")
os.rename("./val/sunflowers", "./val/3_sunflowers")
os.rename("./val/roses", "./val/4_roses")

def format_images(image, label):
    image_res = 224
    formated_image = tf.image.resize(image, (image_res, image_res))/255.0
    return formated_image, label

while True:
    n_images = n_images_waiting()
    if n_images > 1:

        # lets load model like we did in prediction:
        latest_model_version = latest_model_version()
        logging.info(f"Latest model version: {latest_model_version}")

        model_bytes = load_model(latest_model_version) 

        #bytes into path, wont be deleting temp file.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".keras") as temp_file:
            temp_file.write(model_bytes) # model bytes to tempfile.
            temp_file_path = temp_file.name
        
        # load the model
        model = tf.keras.models.load_model(temp_file_path)
        logging.info(f"model: {model.summary(show_trainable=True)}")

        # Use current UNIX time as the version of the model
        model_version = int(time.time())
        iso_time = datetime.fromtimestamp(model_version).isoformat()
        logging.info(
            f"Found {n_images} images in Queue at {model_version} ({iso_time})."
        )

        # Get all the images from the blob storage using messages in queue, deleting them from the queue
        # Note that this is a risk; if the following process fails, the images are lost
        dataset = get_all_from_queue()
        logging.info({len(dataset)})
        images = [image[0] for image in dataset]
        labels = [label[1] for label in dataset]
        logging.info({len(dataset)})

        if len(dataset) > 0:
            train_ds = tf.data.Dataset.from_tensor_slices((images, labels))
            train_ds = train_ds.batch(len(dataset)).shuffle(len(dataset))

            # validation dataset from loaded data
            val_ds = keras.utils.image_dataset_from_directory("./val/",
                                                              validation_split=None,
                                                              seed=123,
                                                              image_size=(224, 224),
                                                              batch_size=32
                                                              )
            
            # prepare batches
            train_batches = train_ds.map(format_images).prefetch(tf.data.AUTOTUNE)
            val_batches = val_ds.map(format_images).prefetch(tf.data.AUTOTUNE)

            # train the model
            history = model.fit(train_batches,
                                epochs=3,
                                batch_size=len(dataset)
                                )

            # evaluate
            model.evaluate(val_batches, verbose=2)
            
            # upload model to blob storage
            model.save("temp_model.keras")
            upload_model("temp_model.keras", f"models/flowersmodel_{model_version}.keras")

            logging.info(f"Model version {model_version} is now available.")
        else:
            logging.info(f"No dataset found")
    else:
        logging.info("Waiting images to process.")

    time.sleep(10)
