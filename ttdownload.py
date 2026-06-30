import asyncio
import aiohttp
import aiofiles
from aiohttp_socks import ProxyConnector
from datetime import datetime
import json
import re
import argparse
from traceback import print_exception
from urllib.parse import unquote
import os
import mimetypes
class TikTokDownloader():
    def __init__(self, site_session: aiohttp.ClientSession = None, api_session: aiohttp.ClientSession = None, proxy: str = None):
        self.site_session = site_session
        self.api_session = api_session
        self.proxy = proxy
        self.close_site_session = None
        self.close_api_session = None
        self.session_choice = None
    @staticmethod
    def make_connector(proxy: str = None):
        if proxy is None:
            return aiohttp.TCPConnector()
        return ProxyConnector.from_url(proxy)
    async def __aenter__(self):
        if self.site_session is None:
            self.site_session = aiohttp.ClientSession(connector=self.make_connector(self.proxy))
            self.close_site_session = True
        if self.api_session is None:
            self.api_session = aiohttp.ClientSession(connector=self.make_connector(self.proxy))
            self.close_api_session = True
        return self
    async def __aexit__(self, exc, exctype, tb):
        if exc:
            print_exception(exc, exctype, tb)
        if self.close_site_session is True:
            await self.site_session.close()
        if self.close_api_session is True:
            await self.api_session.close()
    class InvalidLink(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    class PostUnavailable(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    class SizeTooBig(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    def parse_response(self, response: dict):
        if response['status_code'] != 0:
            return {"type": "error"}

        images = response['item_info']['item_basic'].get('image')
        music = {}
        if response['item_info']['item_basic'].get('music'):
            m = response['item_info']['item_basic'].get('music')['basic']
            music['author'] = m.get('author_name')
            music['title'] = m.get('title')
            music['url'] = m.get('music_play', {}).get('play_url', [])[0]
        stats = {}
        stats['likes'] = response['item_info']['item_stats'].get('digg_count')
        stats['comments'] = response['item_info']['item_stats'].get('comment_count')
        stats['bookmarks'] = response['item_info']['item_stats'].get('collect_count')
        stats['views'] = response['item_info']['item_stats'].get('play_count')
        stats['shares'] = response['item_info']['item_stats'].get('share_count')
        description = response['share_meta'].get('desc')
        if description is not None and description.startswith("%!("):
            description = description.split("string=")[-1][:-1]
        create_time = response['item_info']['item_basic'].get('create_time')
        if images:
            images: list[dict] = images.get("images")
            links = []
            for image in images:
                links.append(image.get("image_url")[0] if isinstance(image.get("image_url"), list) else image.get("image_url"))
            return {"type": "slideshow", "links": links, "music": music, "author": {"username": response['item_info']['item_basic']['creator']['base'].get('unique_id'), "avatar_url": response['item_info']['item_basic']['creator']['base'].get('avatar_larger', [])[0]},
                    'stats': stats, 'description': description, 'date_posted': create_time}
        videos = response['item_info']['item_basic'].get('video')
        if videos:
            videos = videos.get('video_play_info')
            link = videos['play_addr'][0]
            return {"type": "video", "link": link, "music": music, 'stats': stats, 'description': description, 'date_posted': create_time,
                    "author": {"username": response['item_info']['item_basic']['creator']['base'].get('unique_id'), "avatar_url": response['item_info']['item_basic']['creator']['base'].get('avatar_larger', [])[0]},
                    "codec": "h264",}
        return {"type": "error"}
    async def _download(self, url: str, filename: str, maxsize: int = None):
        """
        downloads source from url to filename, returns ext
        """
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.8',
            'cache-control': 'no-cache',
            'origin': 'https://www.tiktok.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.tiktok.com/',
            'sec-ch-ua': '"Brave";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
        }
        async with aiofiles.open(filename, "wb") as f1:
            splitted = url.split("?")
            base_url = splitted[0]

            new_params = {}
            if (len(splitted) == 2):
                params_string = splitted[1]
                for i in params_string.split("&"):
                    key = i.split("=")[0]
                    value = unquote("=".join(i.split("=")[1:]))
                    new_params[key] = value
            session = self.site_session
            if self.session_choice:
                session = self.api_session
            async with session.get(base_url, params=new_params, headers=headers) as r:
                if maxsize and int(r.headers.get('content-length', 0)) > maxsize:
                    raise self.SizeTooBig(f"Video larger than allowed threshold")
                ext = None
                try:
                    ext = mimetypes.guess_extension(r.headers.get("content-type"))
                except:
                    print_exception()
                while True:
                    chunk = await r.content.read(1024)
                    if not chunk:
                        break
                    await f1.write(chunk)
                return ext

    async def download(self, link: str, max_size: int = None):
        """
        Args:
            link (str): link to a post
            max_size (int, optional): max size of video in bytes
        Returns:
            dict: 
                type (str): video / slideshow

                stats (dict): counts of likes, comments, shares, bookmarks

                music (dict): author, title and link to music used in post

                description (str): description used in video

                date_posted (int): timestamp of post creation

                links (list, optional): links of images in post

                link (str, optional): link to video

        """
        link_regex = r"(?:https)?://(?:www\.)?(?:v(?:.*?)\.)?tiktok\.com/\S+"
        if not (link_match := (await asyncio.to_thread(re.search, link_regex, link))):
            raise self.InvalidLink(f"Link unrecognized")
        url = link_match.group()
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.8',
            'cache-control': 'no-cache',
            'origin': 'https://www.tiktok.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.tiktok.com/',
            'sec-ch-ua': '"Brave";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
        }
        async with self.site_session.get(url, headers=headers) as r:
            if r.status not in [200, 204]:
                raise ConnectionError(f"Failed to connect properly to {url} with status code: {r.status}")
            response = await r.text("utf-8")
        item_id_pattern = r"https(?:.*?)/(\d+)/?$"
        item_id = (await asyncio.to_thread(re.search, item_id_pattern, str(r.url).split("?")[0]))
        video_regex = r"\"webapp\.video-detail\":(\{\"itemInfo\":\{\"itemStruct(?:.*?)\}),\"webapp\.a-b\""
        video_match = await asyncio.to_thread(re.search, video_regex, response)
        result = {}
        if not video_match:
            if item_id is None:
                item_id = (await asyncio.to_thread(re.search, item_id_pattern, url))
                if item_id is None:
                    canonical_regex = r"\"canonical\":\"https(?:.*?)(\d+)\""
                    item_id = await asyncio.to_thread(re.search, canonical_regex, response)
                    if item_id is None:
                        async with aiofiles.open("response.txt", "w", encoding="utf-8") as f1:
                            await f1.write(response)
                        raise self.PostUnavailable(f"Couldn't find post info in site source and url")

            params = {
            'app_id': '1988',
            'item_id': item_id.group(1),
            }
            async with self.api_session.get('https://www.tiktok.com/api/reflow/item/detail/', params=params, headers=headers) as r:
                response = await r.json()
            post = self.parse_response(response)
            if post['type'] == 'error':
                raise self.PostUnavailable(f"Couldnt fetch post from api")
            result = post
            self.session_choice = 1
        else:
            video_info = (await asyncio.to_thread(json.loads, video_match.group(1)))['itemInfo']['itemStruct']
            result['type'] = 'video'
            if video_info.get('author') is not None:
                result['author'] = {
                    'username': video_info['author'].get('uniqueId'),
                    'avatar_url': video_info['author'].get('avatarLarger'),
                }
            else:
                result['author'] = {
                    'username': 'author',
                }
            result['stats'] = {
                'likes': video_info['statsV2'].get('diggCount'),
                'shares': video_info['statsV2'].get('shareCount'),
                'comments': video_info['statsV2'].get('commentCount'),
                'views': video_info['statsV2'].get('viewCount'),
                'bookmarks': video_info['statsV2'].get('collectCount'),
                'reposts': video_info['statsV2'].get('repostCount'),
            }
            if video_info.get('music') is not None:
                result['music'] = {
                    'author': video_info['music'].get('authorName'),
                    'title': video_info['music'].get('title'),
                    'url': video_info['music'].get('playUrl')
                }
            else:
                result['music'] = {}
            result['description'] = (video_info['contents'][0].get('desc', '')).encode().decode("unicode_escape") if len(video_info['contents']) > 0 else None
            result['date_posted'] = video_info.get('createTime')
            result['link'] = None
            if max_size is None:
                result['link'] = video_info['video']['bitrateInfo'][0]['PlayAddr']['UrlList'][1]
                result['codec'] = video_info['video']['bitrateInfo'][0]['CodecType']
            else:
                for i in video_info['video']['bitrateInfo']:
                    if int(i['PlayAddr']['DataSize']) < max_size and i['CodecType'] == 'h264':
                        result['link'] = i['PlayAddr']['UrlList'][1]
                        result['codec'] = i['CodecType']
                        break
                if result['link'] is None:
                    for i in video_info['video']['bitrateInfo']:
                        if int(i['PlayAddr']['DataSize']) < max_size:
                            result['link'] = i['PlayAddr']['UrlList'][1]
                            result['codec'] = i['CodecType']
                            break
                if result['link'] is None:
                    raise self.SizeTooBig(f"Size of video formats larger than max_size: {max_size}")
            self.session_choice = 0
        result['filenames'] = []
        if result['type'] == 'slideshow':
            now = str(int(datetime.now().timestamp()))
            if not os.path.exists(f"{result['author']['username']}"):
                os.mkdir(result['author']['username'])
            for idx, url in enumerate(result['links']):
                filename = os.path.join(result['author']['username'], f"{result['author']['username']}-{now}-{idx}")
                ext = await self._download(url, filename)
                if ext is not None:
                    os.rename(filename, filename+ext)
                    filename += ext
                result['filenames'].append(filename)
            filename = os.path.join(result['author']['username'], f"{result['author']['username']}-{now}")
            ext = await self._download(result['music']['url'], filename)
            if ext is not None:
                if ext == ".mp4":
                    ext = ".m4a"
                os.rename(filename, filename+ext)
                filename += ext
            elif ext is None:
                ext = ".mp3"
                os.rename(filename, filename+ext)
                filename += ext
            result['filenames'].append(filename)

        else:
            filename = f"{result['author']['username']}-{datetime.now().timestamp():.0f}.mp4"
            await self._download(result['link'], filename, max_size)
            result['filenames'].append(filename)
        return result

async def main(link: str, proxy: str = None, maxsize: int = None):
    async with TikTokDownloader(proxy=proxy) as ttdownload:
        result = await ttdownload.download(link, max_size=maxsize)
        print(json.dumps(result, indent=4, ensure_ascii=False))
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("link", help="link to post")
    parser.add_argument("--proxy", "-p", help="proxy to use with request")
    parser.add_argument("--maxsize", "-m", help="max size in megabytes of a video", type=float)
    args = parser.parse_args()
    asyncio.run(main(args.link, args.proxy, int(args.maxsize * (1024 * 1024)) if args.maxsize is not None else None))