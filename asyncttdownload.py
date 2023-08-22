from urllib.parse import unquote
import aiohttp, aiofiles, re
from datetime import datetime
import logging
from tqdm.asyncio import tqdm
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
    def __init__(self) -> None:
        pass




    async def download(link: str, mstoken: str, h264: bool = False, h265: bool = False):
        """download tiktok posts
        link (str): link to tiktok post
        mstoken (str): mstoken to use (from cookies)
        h264 (bool): whether to download a h264 codec only
        h265 (bool): whether to download h265 codec only
        by default h264, if both values are true raise twocodecs"""
        pattern1 = r'(https?://)?(www\.)?(vm\.)?tiktok\.com/\S+'
        matches = re.findall(pattern1, link)
        if matches:
            pass
        else:
            raise ttdownload.invalidlink(f'{link} isnt a valid link prolly')
        codec = 'h264' if h264 and not h265 else 'h265' if not h264 and h265 else 'h264' if not h264 and not h265 else None
        if not codec:
            raise ttdownload.twocodecs(f"Please only select one codec")

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
        cookie = {'msToken': mstoken}
        async with aiohttp.ClientSession() as session:
            logging.debug(f"[DOWNLOADING] - {link}")
            async with session.get(link, cookies=cookie, headers=headers) as response:
                if response.status != 200 and response.status != 206:
                    raise ttdownload.requesterror(f'{response.status} code')
                logging.debug('Successfully downloaded webpage')
                responsetext = await response.text()
            pattern = r'\"UrlList\":\[\"(.*?)(?=\")'
            matches = re.findall(pattern, responsetext)
            if not matches:
                raise ttdownload.nomatches('couldnt find urls')
            logging.debug('Successfully found urls')
            codecpattern = r'\"CodecType\":\"(.*?)(?=\")'
            codecmatches = re.findall(codecpattern, responsetext)
            url2 = None
            for url, codecx in zip(matches, codecmatches):
                if codec in codecx:
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
            async with session.get(url, params=params, cookies=cookie, headers=headers) as response:
                if response.status != 200 and response.status != 206:
                    raise ttdownload.forbidden(f"{response.status}\n{await response.text()}")
                logging.debug('Successfully connected to video host, downloading now')
                authorpattern = r'\"author\":\"(.*?)(?=\")'
                authormatches = re.findall(authorpattern, responsetext)
                authorname = authormatches[0]
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
                return filename

            
            
