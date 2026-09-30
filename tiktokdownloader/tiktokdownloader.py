import asyncio
from curl_cffi import AsyncSession, Response
import aiofiles
from datetime import datetime
import json
import re
import argparse
from traceback import print_exception, print_exc
import os
import mimetypes
class TikTokDownloader():
    def __init__(self, site_session: AsyncSession = None, api_session: AsyncSession = None, proxy: str = None):
        self.site_session = site_session
        self.api_session = api_session
        self.proxy = proxy
        self.close_site_session = None
        self.close_api_session = None
        self.session_choice = None
    async def __aenter__(self):
        if self.site_session is None:
            self.site_session = AsyncSession(impersonate="chrome", proxies={"https": self.proxy})
            self.close_site_session = True
        if self.api_session is None:
            self.api_session = AsyncSession(impersonate="chrome", proxies={"https": self.proxy})
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
            'accept-language': 'en-US,en;q=0.7',
            'origin': 'https://www.tiktok.com',
            'priority': 'u=1, i',
            'referer': 'https://www.tiktok.com/',
            'sec-ch-ua': '"Chromium";v="154", "Brave";v="154", "Not A(Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36',
        }

        async with aiofiles.open(filename, "wb") as f1:
            session = self.site_session
            if self.session_choice:
                session = self.api_session

            r: Response = await session.get(url, headers=headers, stream=True)
            if maxsize and int(r.headers.get('content-length', 0)) > maxsize:
                raise self.SizeTooBig(f"Video larger than allowed threshold")
            ext = None
            try:
                ext = mimetypes.guess_extension(r.headers.get("content-type"))
            except:
                print_exc()
            async for chunk in r.aiter_content(1024):
                await f1.write(chunk)
            return ext
    async def newAPI(self, link: str, item_id: str, cookies: dict = None):
        import tiktok_web_signer.xgnarly as xgnarly
        import tiktok_web_signer.xdynosaur as xdynosaur
        raw_qs = (
            "aid=1988&app_name=tiktok_web"
            "&browser_language=en-US&browser_name=Mozilla"
            "&browser_platform=Win32"
            "&browser_version=5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F154.0.0.0%20Safari%2F537.36"
            "&device_id=7691386644755924483&device_platform=web_pc"
            f"&itemId={item_id}"
            "&os=windows&region=PL"
            "&screen_height=800&screen_width=1280"
        ) 
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/154.0.0.0 Safari/537.36"
        )
        sign_opts = dict(
            envcode=65,
            canvas=3535508595,      
            ubcode=14,              
            version="5.3.2",
            scm_version="1.0.0.417",
            total_reqs=3,
            enc_reqs=1,            
        )
        dyno = xdynosaur.encrypt(qs=raw_qs, body="", ua=ua, field_53=link, **sign_opts)
        gnarly = xgnarly.encrypt(qs=raw_qs, body="", ua=ua, **{**sign_opts, "enc_reqs": 4})
        final_url = (
            f"https://www.tiktok.com/api/item/detail/?{raw_qs}"
            f"&X-Dynosaur={dyno}"
            f"&msToken="
            f"&X-Bogus=1"
            f"&X-Gnarly={gnarly}"
        )
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.5",
            "sec-ch-ua": '"Chromium";v="154", "Brave";v="154", "Not A(Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": ua,
        }
        response: Response = await self.site_session.get(final_url, headers=headers, cookies=cookies)
        response_json = await asyncio.to_thread(json.loads, response.text)
        return (response_json)
    def parse_response_new(self, response: dict, max_size: int):
        if response['statusCode'] != 0:
            return {"type": "error"}
        images = response['itemInfo']['itemStruct'].get('imagePost')
        if images:
            music = {}
            if response['itemInfo']['itemStruct'].get('music'):
                m = response['itemInfo']['itemStruct'].get('music')
                music['author'] = m.get('authorName')
                music['title'] = m.get('title')
                music['url'] = m.get('playUrl', [])
            stats = {}
            stats['likes'] = response['itemInfo']['itemStruct']['statsV2'].get('diggCount')
            stats['comments'] = response['itemInfo']['itemStruct']['statsV2'].get('commentCount')
            stats['bookmarks'] = response['itemInfo']['itemStruct']['statsV2'].get('collectCount')
            stats['views'] = response['itemInfo']['itemStruct']['statsV2'].get('playCount')
            stats['shares'] = response['itemInfo']['itemStruct']['statsV2'].get('shareCount')
            description = response['shareMeta'].get('desc')
            if description is not None and description.startswith("%!("):
                description = description.split("string=")[-1][:-1]
            create_time = response['itemInfo']['itemStruct'].get('createTime')
            images: list[dict] = images.get("images")
            links = []
            for image in images:
                links.append(image.get("imageUrl")[0] if isinstance(image.get("imageUrl"), list) else image.get("imageUrl"))
            return {"type": "slideshow", "links": links, "music": music, "author": {"username": response['itemInfo']['itemStruct']['author'].get('uniqueId'), "avatar_url": response['itemInfo']['itemStruct']['author'].get('avatarLarger', [])[0]},
                    'stats': stats, 'description': description, 'date_posted': create_time}
        video_info = response['itemInfo']['itemStruct']
        result = {}
        if video_info.get('video') is not None:
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
            if video_info.get('statsV2') is not None:
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
                result['link'] = (video_info['video']['bitrateInfo'][0]['PlayAddr']['UrlList'][0])
                result['codec'] = video_info['video']['bitrateInfo'][0]['CodecType']
            else:
                for i in video_info['video']['bitrateInfo']:
                    if int(i['PlayAddr']['DataSize']) < max_size:
                        result['link'] = i['PlayAddr']['UrlList'][0]
                        result['codec'] = i['CodecType']
                        break
                if result['link'] is None:
                    for i in video_info['video']['bitrateInfo']:
                        if int(i['PlayAddr']['DataSize']) < max_size:
                            result['link'] = i['PlayAddr']['UrlList'][0]
                            result['codec'] = i['CodecType']
                            break
                if result['link'] is None:
                    raise self.SizeTooBig(f"Size of video formats larger than max_size: {max_size}")
        return result 
    async def download(self, link: str, max_size: int = None, cookies: dict[str, str] = None, nodownload: bool = False):
        """
        Args:
            link (str): link to a post
            max_size (int, optional): max size of video in bytes
            cookies (dict[str, str], optional): cookies to use with requests
            nodownload (bool, optional): skip downloading and just return information on the post
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
        r: Response = await self.site_session.get(url, headers=headers, cookies=cookies, stream=True)
        if r.status_code not in [200, 204]:
            raise ConnectionError(f"Failed to connect properly to {url} with status code: {r.status_code}")
        real_url = r.url
        response = await r.atext()
        item_id_pattern = r"https(?:.*?)/(\d+)/?$"
        item_id = (await asyncio.to_thread(re.search, item_id_pattern, str(r.url).split("?")[0]))
        video_regex = r"\"webapp\.video-detail\":(\{\"itemInfo\":\{\"itemStruct(?:.*?)\}),\"webapp\.a-b\""
        video_match = await asyncio.to_thread(re.search, video_regex, response)
        result = {}
        if video_match is None:
            if item_id is None:
                item_id = (await asyncio.to_thread(re.search, item_id_pattern, url))
                if item_id is None:
                    canonical_regex = r"\"canonical\":\"https(?:.*?)(\d+)\""
                    item_id = await asyncio.to_thread(re.search, canonical_regex, response)
                    if item_id is None:
                        redirectUrl = r"\"redirectUrl\":\"(.*?)\""
                        redirect = await asyncio.to_thread(re.search, redirectUrl, response)
                        if redirect is None:
                            async with aiofiles.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "response.txt"), "w", encoding="utf-8") as f1:
                                await f1.write(response)
                            raise self.PostUnavailable(f"Couldn't find post info in site source and url")
                        redirect = (redirect.group(1)).encode().decode("unicode_escape")
                        item_id = (await asyncio.to_thread(re.search, item_id_pattern, redirect.split("?")[0]))
            real_url = real_url.split("https://")[1].split("?")[0]
            try:
                response = await self.newAPI(real_url, item_id.group(1), cookies=cookies)
                self.session_choice = 0
                post = self.parse_response_new(response, max_size)
                if post['type'] == 'error':
                    raise self.PostUnavailable(f"Couldnt fetch post from api")
                post['api'] = 1
                result = post
            except:
                print_exc()
                params = {
                'app_id': '1988',
                'item_id': item_id.group(1),
                }
                r: Response = await self.api_session.get('https://www.tiktok.com/api/reflow/item/detail/', params=params, headers=headers, cookies=cookies)
                response = r.json()
                post = self.parse_response(response)
                if post['type'] == 'error':
                    raise self.PostUnavailable(f"Couldnt fetch post from api")
                post['api'] = 0
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
            if video_info.get('statsV2') is not None:
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
                result['link'] = video_info['video']['bitrateInfo'][0]['PlayAddr']['UrlList'][0]
                result['codec'] = video_info['video']['bitrateInfo'][0]['CodecType']
            else:
                for i in video_info['video']['bitrateInfo']:
                    if int(i['PlayAddr']['DataSize']) < max_size:
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
        if nodownload is False:
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

async def async_main(link: str, proxy: str = None, maxsize: int = None, nodownload: bool = False):
    async with TikTokDownloader(proxy=proxy) as ttdownload:
        result = await ttdownload.download(link, max_size=maxsize, nodownload=nodownload)
        print(json.dumps(result, indent=4, ensure_ascii=False))
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("link", help="link to post")
    parser.add_argument("--proxy", "-p", help="proxy to use with request")
    parser.add_argument("--maxsize", "-m", help="max size in megabytes of a video", type=float)
    parser.add_argument("--no-download", "-n", help="return only information without downloading post media", action="store_true")
    args = parser.parse_args()
    asyncio.run(async_main(args.link, args.proxy, int(args.maxsize * (1024 * 1024)) if args.maxsize is not None else None, args.no_download))
if __name__ == "__main__":
    main()