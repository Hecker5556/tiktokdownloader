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
usage: ttdownload.py [-h] [--proxy PROXY] [--maxsize MAXSIZE] link

positional arguments:
  link                  link to post

options:
  -h, --help            show this help message and exit
  --proxy PROXY, -p PROXY
                        proxy to use with request
  --maxsize MAXSIZE, -m MAXSIZE
                        max size in megabytes of a video
```
## Python usage
```python
from ttdownload import TikTokDownloader

async def main():
    async with TikTokDownloader() as ttd:
        result = await ttd.download("https://tiktok.com/@author/video/id")
        filenames: list[str] = result['filenames']
        likes = result['stats']['likes']
        music_file = "file.mp3"
        await ttd._download(result['music']['url'], music_file)
        description = result['description']
```
### Extra info
* Downloads video posts and slideshow posts, when slideshow post it also downloads the audio used
* Recommended to use _download function from TikTokDownloader class for downloading media links
* Uses old reflow api / site source, both with different sessions
* Sessions can be given on class initialization
* If description has russian/japanese/chinese etc characters, convert it to utf-16
* Media links might be ip/session specific
* JSON en/de coding and regex searching done asynchronously
* Slideshow images are placed in a folder named by post author