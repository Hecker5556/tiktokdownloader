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
### 5. Get cookies from tiktok, specifically the mstoken, and create a file called env.py, and put the mstoken as follows
```python
mstoken = ""
```
### fill the double quotes with the mstoken
## Usage
```
usage: ttdownload.py [-h] [-h264] [-h265] link

download a tiktok post, you can specify which codec

positional arguments:
  link        link to tiktok video

options:
  -h, --help  show this help message and exit
  -h264       whether to download h264 codec
  -h265       whether to download h265 codec
```
## Python usage (not compatible with running event loop)
```python
import sys
if 'path/to/ttdownload.py' not in sys:
    sys.path.append('path/to/ttdownload.py')
from ttdownload import ttdownload
from env import mstoken
var = ttdownload(link=link, mstoken=mstoken)
filename = var.filename
```
## Python usage async
```python
import sys
if 'path/to/ttdownload.py' not in sys:
    sys.path.append('path/to/ttdownload.py')
from asyncttdownload import ttdownload
from env import mstoken
filename = await ttdownload.download(link=link, mstoken=mstoken)
```
