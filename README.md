# Simple command line based tiktok video downloader
## First time setup
### 1. Download [python](https://python.org)
### 2. in command line 
```bash
git clone https://github.com/Hecker5556/tiktokdownloader.git
```
### 3. 
```bash
cd tiktokdownloader
```
### 4. 
```bash
pip install -r requirements.txt
```
## Usage
```
usage: ttdownload.py [-h] [-w] [-h264] [-h265] [-v] link

download a tiktok post, you can specify which codec

positional arguments:
  link        link to tiktok video

options:
  -h, --help  show this help message and exit
  -w          whether to download watermarked version
  -h264       whether to download h264 codec
  -h265       whether to download h265 codec
  -v          verbose
```
## Python usage (not compatible with running event loop)
```python
import sys
if 'path/to/tiktokdownloader/' not in sys:
    sys.path.append('path/to/tiktokdownloader/')
from tiktokdownloader.ttdownload import ttdownload
filename = ttdownload.download(link=link)
#filenames stored in list if its a slideshow
```
## Python usage async
```python
import sys
if 'path/to/tiktokdownloader/' not in sys:
    sys.path.append('path/to/tiktokdownloader/')
from tiktokdownloader.ttdownload import ttdownload
async def main():
  filename = await ttdownload.async_download(link=link)
```
