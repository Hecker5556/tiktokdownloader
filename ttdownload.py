from urllib.parse import unquote
import aiohttp, aiofiles, asyncio, re, json
from datetime import datetime
import logging
from tqdm.asyncio import tqdm
import argparse
logging.basicConfig(level=logging.DEBUG, format="%(message)s")
class ttdownload:
    class nomatches(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class forbidden(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class twocodecs(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class requesterror(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class invalidlink(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    def __init__(self, link: str, mstoken: str, watermark: bool = False, h264: bool = False, h265: bool = False):
        """download tiktok posts
        link (str): link to tiktok post
        mstoken (str): mstoken to use (from cookies)
        watermarked (bool, False): download watermarked version
        h264 (bool): whether to download a h264 codec only
        h265 (bool): whether to download h265 codec only
        by default h264, if both values are true raise twocodecs"""
        self.codec = 'h264' if h264 and not h265 else 'h265' if not h264 and h265 else 'h264' if not h264 and not h265 else None
        if not self.codec:
            raise self.twocodecs(f"Please only select one codec")
        pattern1 = r'(https?://)?(www\.)?(v(.*?)\.)?tiktok\.com/\S+'
        matches = re.findall(pattern1, link)
        if matches:
            self.link = link
        else:
            raise self.invalidlink(f'{link} isnt a valid link prolly')
        self.cookie = {'msToken': mstoken}
        self.headers = {
            'authority': 'v16-webapp-prime.tiktok.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'origin': 'https://www.tiktok.com',
            'range': 'bytes=0-',
            'referer': 'https://www.tiktok.com/',
            'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Brave";v="116"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'video',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        }
        self.watermark = watermark
        asyncio.run(self.download())
        logging.debug(f'downloaded to {self.filename} codec {self.codec}')
    async def download(self):
        async with aiohttp.ClientSession() as session:
            logging.debug(f"[DOWNLOADING] - {self.link}")
            async with session.get(self.link, cookies=self.cookie, headers=self.headers) as response:
                if response.status != 200 and response.status != 206:
                    raise self.requesterror(f'{response.status} code')
                logging.debug('Successfully downloaded webpage')
                responsetext = await response.text()
            authorpattern = r'\"author\":\"(.*?)(?=\")'
            authormatches = re.findall(authorpattern, responsetext)
            authorname = authormatches[0]
            if authorname == "author":
                authormatches = re.findall(r"\"uniqueId\":\"(.*?)\"", responsetext)
                authorname = authormatches[0]
            if '"imagePost":{"images":[{"imageURL":' in responsetext:
                logging.info("not a video, slideshow")
                pattern = r'\{\"images\":(?:.*?)\"title\":(?:.*?)}'
                matches = re.findall(pattern, responsetext)
                images = json.loads(matches[0])
                filenames = []
                for index, image in enumerate(images["images"]):
                    url = image["imageURL"]["urlList"][0]
                    filename = f"{authorname}-{index}-{round(datetime.now().timestamp())}.jpeg"
                    async with session.get(url) as r:
                        progress = tqdm(total=int(r.headers.get("content-length")), unit='iB', unit_scale=True)
                        async with aiofiles.open(filename, 'wb') as f1:
                            while True:
                                chunk = await r.content.read(1024)
                                if not chunk:
                                    break
                                await f1.write(chunk)
                                progress.update(len(chunk))
                        progress.close()
                    filenames.append(filename)
                self.filename = filenames
                self.codec = "images (jpeg)"
                return self
            if not self.watermark:
                pattern = r'\"UrlList\":\[\"(.*?)(?=\")'
            else:
                pattern = r"\"downloadAddr\":\"(.*?)\""
            matches = re.findall(pattern, responsetext)
            if not matches:
                raise self.nomatches('couldnt find urls')
            logging.debug('Successfully found urls')
            codecpattern = r'\"CodecType\":\"(.*?)(?=\")'
            codecmatches = re.findall(codecpattern, responsetext)
            url2 = None
            for url, codec in zip(matches, codecmatches):
                if self.codec in codec:
                    url2 = url
                    break
            if not url2:
                logging.debug('no h264, resorting to h265')
                url2 = matches[0]
            else:
                logging.debug(f'Successfully found video with codec: {self.codec}')
            url1 = unquote(url2).encode('utf-8').decode('unicode_escape')
            url = url1.split('?')[0]
            oldparams = url1.split('?')[1].split('&')
            params = {}
            for i in oldparams:
                params[i.split('=')[0]] = i.split('=')[1]
            async with session.get(url, params=params, cookies=self.cookie, headers=self.headers) as response:
                if response.status != 200 and response.status != 206:
                    raise self.forbidden(f"{response.status}\n{await response.text()}")
                logging.debug('Successfully connected to video host, downloading now')

                filename = f"{authorname}-{int(datetime.now().timestamp())}.mp4"
                async with aiofiles.open(filename, 'wb') as f1:
                    totalsize = float(response.headers.get('content-length'))
                    progress = tqdm(total=totalsize, unit='iB', unit_scale=True)
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        await f1.write(chunk)
                        progress.update(len(chunk))
                    progress.close()
                self.filename = filename
                return self

            
            
    def __call__(self):
        asyncio.run(self.download())
    def __enter__(self):
        asyncio.run(self.download())
        return self
    def __exit__(self, exctype, excvalue, traceback):
        if exctype:
            print(f"{exctype}\n{excvalue}\n{traceback}")
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='download a tiktok post, you can specify which codec')
    parser.add_argument("link", help='link to tiktok video')
    parser.add_argument("-w", action="store_true", help="whether to download watermarked version")
    parser.add_argument("-h264", action="store_true", help="whether to download h264 codec")
    parser.add_argument("-h265", action="store_true", help="whether to download h265 codec")
    args = parser.parse_args()
    from env import mstoken
    ttdownload(link=args.link, mstoken=mstoken, watermark=args.w, h264=args.h264, h265=args.h265)