import os
import glob
import io
import asyncio
import aiohttp
from PIL import Image, ImageSequence
import firebase_admin
from firebase_admin import credentials, storage

# Initialize Firebase
cred = credentials.Certificate("./novabl0x-ae3e6a3e422d.json")
firebase_app = firebase_admin.initialize_app(cred, {
    "storageBucket": "novabl0x.appspot.com"
})
bucket = storage.bucket()

processed_prefix = "processed_"

# Define the target width of the images/gifs
target_width = 300


def compress_gif(image, width, height):
    # resize all frames of the gif using the LZW compression algorithm
    frames = []
    for frame in ImageSequence.Iterator(image):
        frame = frame.resize((width, height), resample=Image.Resampling.LANCZOS)
        frames.append(frame)

    # Save the compressed frames to a new image
    compressed_image = io.BytesIO()
    frames[0].save(compressed_image, format="GIF", save_all=True, append_images=frames[1:],
                   optimize=True)
    compressed_image.seek(0)
    compressed_image = Image.open(compressed_image)
    return compressed_image


# Define the async function to compress and upload images
async def compress_and_upload_image_async(session, image_url, width, folder,
                                          local=False):
    if local:
        with open(image_url, "rb") as f:
            image = Image.open(f)
    else:
        async with session.get(image_url) as response:
            content = await response.read()
            image = Image.open(io.BytesIO(content))

    # Calculate the height using the aspect ratio
    aspect_ratio = image.width / image.height
    target_height = int(target_width / aspect_ratio)

    # Check the file format and use the appropriate compression method
    file_format = image.format
    if file_format == "GIF":
        # compress the GIF using the LZW compression algorithm
        compressed_image = compress_gif(image, width, target_height)
        image_buffer = io.BytesIO()
        compressed_image.save(image_buffer, format="GIF", save_all=True, optimize=True)
        content_type = "image/gif"
    else:
        # Compress the JPEG using the Lanczos resampling algorithm
        compressed_image = image.resize((width, target_height), resample=Image.Resampling.LANCZOS)
        compressed_image = compressed_image.convert('RGB')
        image_buffer = io.BytesIO()
        compressed_image.save(image_buffer, format="JPEG", quality=85)
        content_type = "image/jpeg"

    image_buffer.seek(0)

    image_name = image_url.split("/")[-1]
    firebase_path = f"{folder}/{image_name}"
    blob = bucket.blob(firebase_path)
    blob.upload_from_file(image_buffer, content_type=content_type)
    print(f"Image uploaded to: {firebase_path}")

    return image_name


# Define the function to process image batches concurrently
async def process_image_batch(urls, width, folder, local=False):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for image_url in urls:
            task = asyncio.ensure_future(
                compress_and_upload_image_async(session, image_url, width, folder,
                                                local))
            tasks.append(task)
        processed = await asyncio.gather(*tasks)
    return processed


# Define the function to read image URLs from a text file and skip processed URLs
def read_image_urls_from_file(file_path):
    with open(file_path, "r") as f:
        urls = [line.strip() for line in f if not line.startswith(processed_prefix)]
    return urls


# Define the function to update the processed image URLs in the text file
def update_processed_urls(file_path, images):
    with open(file_path, "r") as f:
        lines = f.readlines()

    with open(file_path, "w") as f:
        for line in lines:
            url = line.strip()
            if url in images:
                f.write(f"{processed_prefix}{url}\n")
            else:
                f.write(f"{url}\n")


# Process all text files in the specified folder
text_files_folder = "./list_to_compress"
text_files = glob.glob(os.path.join(text_files_folder, "*.txt"))

for text_file_path in text_files:
    individual_file_name = os.path.basename(text_file_path)

    if not text_file_path.startswith(individual_file_name):
        image_urls = read_image_urls_from_file(text_file_path)
        firebase_folder = os.path.splitext(os.path.basename(text_file_path))[0]
        processed_images = asyncio.run(process_image_batch(image_urls, target_width, firebase_folder))
        update_processed_urls(text_file_path, processed_images)
        os.rename(text_file_path,
                  os.path.join(text_files_folder, f"{processed_prefix}{os.path.basename(text_file_path)}"))
