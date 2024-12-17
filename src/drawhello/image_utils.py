import zlib
import numpy as np
import logging

from PIL import Image, ImageChops
from base64 import b64encode, b64decode

def trim(im, border):
    bg = Image.new(im.mode, im.size, border)
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)

def to_40x20_binary(image_data:Image) -> Image:
    """Crop the surrounding white space and resize the image to 40x20 as grayscale image.
    """

    # Convert to grayscale
    img = image_data.convert("L")

    # Trim out white pixels
    img = trim(img, 255)

    # Use the nearest neighbor method to preserve the pixel values
    img = img.resize((40, 20), resample=Image.NEAREST)

    # Binarize the image using custom threshold
    img = img.point(lambda p: p > 225 and 255)

    # Convert to black and white
    img = img.convert("1")

    return img

def serialize_grayscale(image_data:Image, label:int=None) -> str:
    """Compress the image and convert it to base64.
    """

    # Check that the image is in B&W
    assert image_data.mode == "1"

    # Compress the image data
    logging.info(f"Image data before compression: {np.asarray(image_data, dtype='uint8').flatten()}")
    img_compressed = zlib.compress(np.asarray(image_data, dtype="uint8").flatten().tobytes())
    logging.info(f"Image data as compressed: {img_compressed}")

    if label is not None:
        assert label in [0, 1]
        logging.info(f"Adding label {label} to the image.")
        
        img_compressed = img_compressed + label.to_bytes(1, byteorder="big")

    # Convert to base64
    return b64encode(img_compressed).decode("utf-8")


def deserialize_grayscale(compressed_b64:str, size=(20, 40), has_label=False) -> tuple[Image.Image, int]:
    """Decompress the base64 string and convert it to an image.
    """

    label=None

    # Base64 => bytes
    decoded = b64decode(compressed_b64)

    if has_label:
        # Extract the label
        label = int.from_bytes(decoded[-1:], byteorder="big")
        decoded = decoded[:-1]

    uncompressed = zlib.decompress(decoded)

    # Convert back to numpy array
    img = Image.fromarray(np.frombuffer(uncompressed, dtype=np.bool_).reshape(size))

    return img, label

if __name__ == "__main__":

    # Create fake image data
    image_data =np.random.randint(0, 255, (20, 40), dtype=np.uint8)
    img = Image.fromarray(image_data)
    img = img.convert('1')

    # SerDe without Label
    serialized = serialize_grayscale(img)
    deserialized, label = deserialize_grayscale(serialized)
    assert img.size == deserialized.size
    assert np.all(np.array(img) == np.array(deserialized))
    print("Non-label serialization and deserialization successful.")
    print("=" * 20)
    
    # SerDe with Label 0
    serialized = serialize_grayscale(img, label=0)
    deserialized, label = deserialize_grayscale(serialized, has_label=True)
    assert img.size == deserialized.size
    assert label == 0
    assert np.all(np.array(img) == np.array(deserialized))
    print("Labeled data serialization and deserialization successful.")