import os
import glob
import io
import asyncio
import aiohttp
from PIL import Image, ImageSequence
import firebase_admin
from firebase_admin import credentials, storage
import base64
from urllib.parse import urlparse
from typing import List, Tuple
from PIL import Image
from io import BytesIO
from tqdm import tqdm


# Initialize Firebase
cred = credentials.Certificate("./novabl0x-ae3e6a3e422d.json")
firebase_app = firebase_admin.initialize_app(cred, {
    "storageBucket": "novabl0x.appspot.com"
})
bucket = storage.bucket()

processed_prefix = "processed_"

# Process all text files in the specified folder
text_files_folder = "./list_to_compress"

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

##remove file extention and return the name
def get_file_name(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]

# Define the async function to compress and upload images
async def compress_and_upload_image_async(session, image_url, width, folder, local=False, base64_data=None):
    try:
        if base64_data:
            index, data = base64_data
            try:
                img_data = data.split(',')[1]
                img_bytes = base64.b64decode(img_data)
                image = Image.open(io.BytesIO(img_bytes))
            except Exception as e:
                print(f"Error decoding base64 data: {str(e)}")
                return None
            image_name = f"image_{index}.{image.format.lower()}"
        elif local:
            with open(image_url, "rb") as f:
                image = Image.open(f)
            image_name = image_url.split("/")[-1]
        else:
            async with session.get(image_url) as response:
                content = await response.read()
                image = Image.open(io.BytesIO(content))
            image_name = image_url.split("/")[-1]

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

        firebase_path = f"{folder}/{get_file_name(image_name)}"
        blob = bucket.blob(firebase_path)
        blob.upload_from_file(image_buffer, content_type=content_type)
        print(f"Image uploaded to: {firebase_path}")

        return image_name
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None


# Define the function to process image batches concurrently
async def process_image_batch(urls, width, folder, local=False, base64_data=None):
    async with aiohttp.ClientSession() as session:
        tasks = []
        if base64_data:
            for index, data in base64_data:
                task = asyncio.ensure_future(
                    compress_and_upload_image_async(session, None, width, folder,
                                                    base64_data=(index, data)))
                tasks.append(task)
        else:
            for image_url in urls:
                task = asyncio.ensure_future(
                    compress_and_upload_image_async(session, image_url, width, folder,
                                                    local))
                tasks.append(task)
        processed = await asyncio.gather(*tasks)
        return len([p for p in processed if p is not None])  # Filter out unsuccessful uploads

# Define the function to update the processed image URLs in the text file
def update_processed_urls(file_path, processed_count, base64_indices=None):
    with open(file_path, "r") as f:
        lines = f.readlines()

    with open(file_path, "w") as f:
        for index, line in enumerate(lines):
            if index < processed_count or (base64_indices and index in base64_indices):
                f.write(f"{processed_prefix}{line}")
            else:
                f.write(line)

def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def split_contents(file_path: str) -> Tuple[List[Tuple[int, str]], List[Tuple[int, str]]]:
    urls = []
    base64_data = []

    with open(file_path, 'r') as file:
        for index, line in enumerate(file):
            line = line.strip()

            if line.startswith('processed_'):
                continue

            if is_valid_url(line):
                urls.append((index, line))
            elif line.startswith('data:'):
                base64_data.append((index, line))

    return urls, base64_data

def add_processed_prefix(file_path: str, index: int) -> None:
    lines = []
    with open(file_path, 'r') as file:
        lines = file.readlines()

    if not lines[index].startswith('processed_'):
        lines[index] = 'processed_' + lines[index]

    with open(file_path, 'w') as file:
        file.writelines(lines)

def base64_to_image(base64_str: str) -> Image.Image:
    img_data = base64_str.split(',')[1]
    img_bytes = base64.b64decode(img_data)
    img_buffer = BytesIO(img_bytes)
    return Image.open(img_buffer)


def process_list_of_image_list_folder(text_files_folder) -> None:
    text_files = glob.glob(os.path.join(text_files_folder, "*.txt"))

    for text_file_path in text_files:
        individual_file_name = os.path.basename(text_file_path)

        if not individual_file_name.startswith(processed_prefix):
            image_urls, base64_data = split_contents(text_file_path)

            firebase_folder = os.path.splitext(os.path.basename(text_file_path))[0]
            processed_images = asyncio.run(process_image_batch(image_urls, target_width, firebase_folder))
            update_processed_urls(text_file_path, processed_images)

            processed_base64_images = asyncio.run(
                process_image_batch([], target_width, firebase_folder, base64_data=base64_data))
            update_processed_urls(text_file_path, processed_base64_images,
                                  base64_indices=[x[0] for x in base64_data if x[1].startswith(processed_prefix)])

            os.rename(text_file_path,
                      os.path.join(text_files_folder, f"{processed_prefix}{os.path.basename(text_file_path)}"))


def start():
    process_list_of_image_list_folder(text_files_folder)

if __name__ == '__main__':
    start()