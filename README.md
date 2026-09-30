# Simple command line based tiktok video downloader
## First time setup
### 1. Download [python](https://python.org)
### 2. in command line 
```
pip install "git+https://github.com/Hecker5556/tiktokdownloader"
```
## Usage
```
usage: tiktokdownloader [-h] [--proxy PROXY] [--maxsize MAXSIZE] [--no-download] link

positional arguments:
  link                  link to post

options:
  -h, --help            show this help message and exit
  --proxy PROXY, -p PROXY
                        proxy to use with request
  --maxsize MAXSIZE, -m MAXSIZE
                        max size in megabytes of a video
  --no-download, -n     return only information without downloading post media
```
## Python usage
```python
from tiktokdownloader import TikTokDownloader

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
* JSON parsing and regex searching done asynchronously
* Slideshow images are placed in a folder named by post author