###Firebase Image Compression Tool
This tool uses Python, Firebase, and PIL (Python Imaging Library) to compress and upload images/gifs to Firebase Storage. The tool reads a list of image URLs from text files, compresses them to the desired size, and uploads them to Firebase Storage. The processed URLs are then marked in the text file to avoid re-processing.

##Dependencies
This tool requires the following Python packages:

  aiohttp
  firebase_admin
  Pillow

##How to Use
  Clone the repository.
  Install the required packages using pip: pip install -r requirements.txt.
  Set up Firebase Storage and download the json file for authentication.
  Place the json file in the same directory as the script and update the path in the cred variable.
  Create a folder containing text files with lists of image URLs to compress. Each text file should contain one URL per line.
  Run the script: python compress.py.
  The script will iterate through all the text files in the specified folder, compress and upload the images, and mark the processed URLs in the respective text file.
