from urllib.parse import unquote
import aiohttp, aiofiles, re, json, requests
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
    def download(link: str, watermark: bool = False, h264: bool = True, h265: bool = False, verbose: bool = False):
        """download tiktok posts
        link (str): link to tiktok post
        mstoken (str): mstoken to use (from cookies)
        watermarked (bool, False): download watermarked version
        h264 (bool): whether to download a h264 codec only
        h265 (bool): whether to download h265 codec only
        by default h264, if both values are true, download first one that finds"""
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")
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
        session = requests.Session()
        r = session.get(link, headers=headers, stream=True)
        logging.debug(f"Response Code: {r.status_code}")
        if r.status_code not in [200, 206]:
            raise ttdownload.request_error(f"Failed to grab web source, code: {r.status_code}")
        response = r.text
        authorpattern = r'\"author\":\"(.*?)(?=\")'
        authormatches = re.findall(authorpattern, response)
        if authormatches:
            authorname = authormatches[0]
            logging.debug(f"Author name first attempt: {authorname}")
        else:
            authorname = "author"
        if authorname == "author":
            authormatches = re.findall(r"\"uniqueId\":\"(.*?)\"", response)
            authorname = authormatches[0]
            logging.debug(f"Author name second attempt: {authorname}")
        if '"imagePost":{"images":[{"imageURL":' in response:
            logging.info("Downloading slideshow")
            pattern = r'\{\"images\":(?:.*?)\"title\":(?:.*?)}'
            matches = re.findall(pattern, response)
            images = json.loads(matches[0])
            filenames = []
            for index, image in enumerate(images["images"]):
                url = image["imageURL"]["urlList"][0]
                filename = f"{authorname}-{index}-{round(datetime.now().timestamp())}.jpeg"
                r = session.get(url, stream=True)
                with tqdm(total=int(r.headers.get("content-length")), unit='iB', unit_scale=True) as progress:
                    with open(filename, 'wb') as f1:
                        for data in r.iter_content(1024):
                            f1.write(data)
                            progress.update(len(data))
                filenames.append(filename)
            return filenames
        if not watermark:
            pattern = r'\"UrlList\":\[\"(.*?)(?=\")'
        else:
            pattern = r"\"downloadAddr\":\"(.*?)\""
        matches = re.findall(pattern, response)
        if not matches:
            raise ttdownload.nomatches('couldnt find urls')
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
        r = session.get(url, params=params, headers=headers, stream=True)
        if r.status_code not in [200, 206]:
            raise ttdownload.request_error(f"Failed to download! Code: {r.status_code}")
        with tqdm(total=int(r.headers.get("content-length")), unit='iB', unit_scale=True) as progress:
            with open(filename, 'wb') as f1:
                for data in r.iter_content(1024):
                    f1.write(data)
                    progress.update(len(data))
        session.close()
        return filename
    async def async_download(link: str, watermark: bool = False, h264: bool = True, h265: bool = False, verbose: bool = False):
        """download tiktok posts
        link (str): link to tiktok post
        mstoken (str): mstoken to use (from cookies)
        watermarked (bool, False): download watermarked version
        h264 (bool): whether to download a h264 codec only
        h265 (bool): whether to download h265 codec only
        by default h264, if both values are true, downloads firest one that finds"""
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(message)s")
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
        async with aiohttp.ClientSession() as session:
            async with session.get(link, headers=headers) as r:

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
                authorname = authormatches[0]
                logging.debug(f"Author name second attempt: {authorname}")
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
                raise ttdownload.nomatches('couldnt find urls')
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
    parser = argparse.ArgumentParser(description='download a tiktok post, you can specify which codec')
    parser.add_argument("link", help='link to tiktok video')
    parser.add_argument("-w", action="store_true", help="whether to download watermarked version")
    parser.add_argument("-h264", action="store_true", help="whether to download h264 codec")
    parser.add_argument("-h265", action="store_true", help="whether to download h265 codec")
    parser.add_argument("-v", action="store_true", help="verbose")
    args = parser.parse_args()
    ttdownload.download(link=args.link, watermark=args.w, h264=args.h264, h265=args.h265, verbose=args.v)