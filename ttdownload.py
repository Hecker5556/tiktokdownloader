from urllib.parse import unquote
import aiohttp, aiofiles, re, json
from datetime import datetime
import logging
from tqdm import tqdm
import argparse
class ttdownload:
    class nomatches(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class request_error(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    class invalidlink(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    def parse_response(self, response: dict):
        if response['status_code'] != 0:
            return {"type": "error"}
        images = response['item_info']['item_basic'].get('image')
        if images:
            images: list[dict] = images.get("images")
            links = []
            for image in images:
                links.append(image.get("image_url")[0] if isinstance(image.get("image_url"), list) else image.get("image_url"))
            return {"type": "slideshow", "links": links}
        videos = response['item_info']['item_basic'].get('video')
        if videos:
            videos = videos.get('video_play_info')
            videotype = "play_addr"
            if self.watermark == True:
                videotype = "download_addr"
            links = []
            for video in videos[videotype]:
                links.append(video[0] if isinstance(video, list) else video)
            return {"type": "video", "links": links}
        return {"type": "error"}
    async def get_api_response(self, item_id: int, session: aiohttp.ClientSession):
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.6',
            'sec-ch-ua': '"Brave";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
        }
        params = {
            'app_id': '1233',
            'item_id': item_id,
        }
        async with session.get('https://www.tiktok.com/api/reflow/item/detail/', params=params, headers=headers) as r:
            response = json.loads(await r.text(encoding="utf-8"))
        return self.parse_response(response)
    async def _download(self, link: str, filename: str, session: aiohttp.ClientSession, params: dict = None, headers: dict = None):
        async with aiofiles.open(filename, 'wb') as f1:
            async with session.get(link, params=params, headers=headers) as r:
                if r.status not in [200, 206]:
                    raise self.request_error(f"failed to get {r.url}, status {r.status}")
                progress = tqdm(total=int(r.headers.get("content-length")) if r.headers.get("content-length") else None, unit="iB", unit_scale=True)
                while True:
                    chunk = await r.content.read(1024)
                    if not chunk:
                        break
                    await f1.write(chunk)
                    progress.update(len(chunk))
    async def async_download(self, link: str, watermark: bool = False, h264: bool = True, h265: bool = False, verbose: bool = False):
        """download tiktok posts
        link (str): link to tiktok post
        watermarked (bool, False): download watermarked version
        h264 (bool): whether to download a h264 codec only
        h265 (bool): whether to download h265 codec only
        by default h264, if both values are true, downloads first one that finds"""
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")
        self.watermark = watermark
        link_pattern = r"(?:https)?://(?:www\.)?(?:v(?:.*?)\.)?tiktok\.com/\S+"
        link = re.findall(link_pattern, link)
        if not link:
            raise ttdownload.invalidlink(f"the link is invalid or the regex cant match it!")
        if h264 and h265:
            codecs = ["h264", "h265_hvc1"]
        elif h264:
            codecs = "h264"
        elif h265:
            codecs = "h265_hvc1"
        else:
            codecs = "h264"
        link = link[0]
        headers = {
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
        cookies = {
            "tt-target-idc": "useast2a",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(link, headers=headers, cookies=cookies) as r:
                logging.debug(f"Response Code: {r.status}")
                if r.status not in [200, 206]:
                    raise ttdownload.request_error(f"Failed to grab web source, code: {r.status}")
                response = await r.text()
            authorpattern = r'\"author\":\"(.*?)(?=\")'
            authormatches = re.findall(authorpattern, response)
            if authormatches:
                authorname = authormatches[0]
                logging.debug(f"Author name first attempt: {authorname}")
            else:
                authorname = "author"
            if authorname == "author":
                authormatches = re.findall(r"\"uniqueId\":\"(.*?)\"", response)
                if authormatches:
                    authorname = authormatches[0]
                else:
                    authormatches = re.findall(r'\"canonical\":\"(.*?)\"', response)
                    if authormatches:
                        authortemp = unquote(authormatches[0]).replace("\\u002F", "/")
                        authormatches = re.findall(r'https://(?:www\.)?tiktok\.com/@(.*?)/', authortemp)
                        if authormatches:
                            authorname = authormatches[0]
                        else:
                            authorname = "author"
                    else:
                        authorname = "author"
                logging.debug(f"Author name second attempt: {authorname}")
            full_link = re.findall(r'\"canonical\":\"(.*?)\"', response)
            if full_link:
                item_id = re.findall(r'https://(?:www\.)?tiktok\.com/@(?:.*?)/(?:.*?)/(\d*?)$', full_link[0].replace("\\u002F", "/"))
                logging.debug(f"item_id: {item_id[0]}")
                api_response = await self.get_api_response(item_id[0], session)
                if api_response['type'] != 'error' and api_response['type'] != 'video':
                    # couldnt figure out how to download videos from the api, plus theyd be watermarked anyways
                    logging.info(f"downloading {api_response['type']} from api")
                    filenames = []
                    extension = 'jpeg'
                    for index, i in enumerate(api_response['links']):
                        filename = f"{authorname}-{index}-{int(datetime.now().timestamp())}.{extension}"
                        await self._download(i, filename, session, headers=headers)
                        filenames.append(filename)
                    return filenames
            if '"imagePost":{"images":[{"imageURL":' in response:
                logging.info("Downloading slideshow")
                pattern = r'\{\"images\":(?:.*?)\"title\":(?:.*?)}'
                matches = re.findall(pattern, response)
                images = json.loads(matches[0])
                filenames = []
                for index, image in enumerate(images["images"]):
                    url = image["imageURL"]["urlList"][0]
                    filename = f"{authorname}-{index}-{round(datetime.now().timestamp())}.jpeg"
                    async with session.get(url) as r:
                        with tqdm(total=int(r.headers.get("content-length")), unit='iB', unit_scale=True) as progress:
                            async with aiofiles.open(filename, 'wb') as f1:
                                while True:
                                    chunk = await r.content.read(1024)
                                    if not chunk:
                                        break
                                    await f1.write(chunk)
                                    progress.update(len(chunk))
                    filenames.append(filename)
                return filenames
            if not watermark:
                pattern = r'\"UrlList\":\[\"(.*?)(?=\")'
            else:
                pattern = r"\"downloadAddr\":\"(.*?)\""
            matches = re.findall(pattern, response)
            if not matches:
                pattern = r"\"video\":((?:.*?)VQScore\":\"\d+\"\})"
                matches = re.search(pattern, response)
                if not matches:
                    raise ttdownload.nomatches('couldnt find urls')
                else:
                    video_info = json.loads(matches.group(1))
                    if watermark:
                        video_url = video_info.get("downloadAddr").encode().decode("unicode_escape")
                    else:
                        video_url = video_info.get("playAddr").encode().decode("unicode_escape")
                    filename = f"{authorname}-{round(datetime.now().timestamp())}.mp4"
                    async with session.get(video_url, headers=headers) as r:
                        with tqdm(total=int(r.headers.get("content-length")), unit='iB', unit_scale=True) as progress:
                            async with aiofiles.open(filename, 'wb') as f1:
                                while True:
                                    chunk = await r.content.read(1024)
                                    if not chunk:
                                        break
                                    await f1.write(chunk)
                                    progress.update(len(chunk))
                    return filename
            codecpattern = r'\"CodecType\":\"(.*?)(?=\")'
            codecmatches = re.findall(codecpattern, response)
            url2 = None
            for url, codec in zip(matches, codecmatches):
                if codec in codecs:
                    url2 = url
                    break
            if not url2:
                logging.debug('no h264, resorting to h265')
                url2 = matches[0]
            else:
                logging.debug(f'Successfully found video with codec: {codec}')
            url1 = unquote(url2).encode('utf-8').decode('unicode_escape')
            url = url1.split('?')[0]
            oldparams = url1.split('?')[1].split('&')
            params = {}
            for i in oldparams:
                params[i.split('=')[0]] = i.split('=')[1]
            filename = f"{authorname}-{round(datetime.now().timestamp())}.mp4"
            async with session.get(url, params=params, headers=headers) as r:
                with tqdm(total=int(r.headers.get("content-length")), unit='iB', unit_scale=True) as progress:
                    async with aiofiles.open(filename, 'wb') as f1:
                        while True:
                            chunk = await r.content.read(1024)
                            if not chunk:
                                break
                            await f1.write(chunk)
                            progress.update(len(chunk))
            return filename

if __name__ == '__main__':
    import asyncio
    parser = argparse.ArgumentParser(description='download a tiktok post, you can specify which codec')
    parser.add_argument("link", help='link to tiktok video')
    parser.add_argument("-w", action="store_true", help="whether to download watermarked version")
    parser.add_argument("-h264", action="store_true", help="whether to download h264 codec")
    parser.add_argument("-h265", action="store_true", help="whether to download h265 codec")
    parser.add_argument("-v", action="store_true", help="verbose")
    args = parser.parse_args()
    asyncio.run(ttdownload().async_download(link=args.link, watermark=args.w, h264=args.h264, h265=args.h265, verbose=args.v))