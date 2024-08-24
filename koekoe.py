A = ""
from lxml import html as html_
import requests
import re
import time
from pathvalidate import sanitize_filename
import pathlib
import os
import sys
from datetime import datetime, timedelta

class KoekoeException_ServerError(Exception):
    pass
class KoekoeException_NetworkError(Exception):
    pass
class KoekoeException_Limiter(Exception):
    pass


with open("archive.txt", "a") as f:
    f.write("")
with open("archive.txt", "r") as f:
    archive_list = f.readlines()
archive_list = set(archive_list)

class Session:
    user_agent = "Mozilla/5.0 (iPhone; CPU OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/14E304 Safari/605.1.15"
    
    def __init__(self):
        self._session = requests.session()
        self._session.headers.update({"User-Agent": self.user_agent})
        self.requests_count = 0

    def get(self, *arrgs, **kwarrgs):
        time.sleep(0.01)
        if self.requests_count >= 500:
            raise KoekoeException_Limiter
        self.requests_count += 1
        r = getattr(self._session, "get")(*arrgs, **kwarrgs)
        return r
session = Session()


def add_archive(url: str, filepath="archive.txt"):
    with open(filepath, "a") as f:
        f.write(url+"\n")

def parse_postdate(date_text):
    unit = {"日前": "days", "時間前": "hours", "分前": "minutes"}
    old = []
    post_date = ""
    now = datetime.now()
    for key, value in unit.items():
        if key in date_text:
            old = {value: int(date_text.replace(key, ""))}
            post_date = now - timedelta(**old)
            post_date = post_date.strftime(f"%Y-%m-%d")
            break
    else:
        #yy/mm/dd
        parts = date_text.split('/')
        year = int(parts[0])
        year += 2000 
        month = parts[1].zfill(2)
        day = parts[2].zfill(2)
        post_date = "{0}-{1}-{2}".format(year,month,day) 
    
    return str(post_date)

def get_html(url):
    retry = 2
    for i in range(retry):
        try:
            time.sleep(0.1)
            response = session.get(url)
            response.raise_for_status()
            break
        except requests.HTTPError:
            if 500 <= response.status_code <= 599:
                raise KoekoeException_ServerError
            continue
        except requests.Timeout:
            raise KoekoeException_ServerError
    else:
        raise KoekoeException_NetworkError
    return response.text


def get_postlist(url: str, limit = 100) -> list:
    
    limit_page = limit

    postlist = []
    for i in range(limit_page):
        postlist_ = []
        print("ページ数: {0} URL: {1}".format(i+1, url))
        html = get_html(url)
        tree = html_.fromstring(html)
        
        a_tags = tree.xpath('//a[contains(@href, "detail") and contains(@title, "の投稿")]')
        
        if a_tags:
            j = 0
            for a_tag in a_tags:
                if not j % 2 == 0:
                    link = "https://koe-koe.com/" + a_tag.get("href")
                    username = a_tag.text_content()
                    title = re.sub(r"^.|.{4}$", "", a_tag.get("title")) 
                    postlist_.append({"link": link, "username": username, "title": title, "date": ""})
                j += 1
        
        p_date_tags = tree.xpath('//p[@class="meta" and contains(text(), "@")]')
        j = 0
        for p_tag in p_date_tags:
            date = parse_postdate(p_tag.text_content().split("@")[-1])
            postlist_[j]["date"] = date
            j+=1

        next_link = tree.xpath('//*[@id="content"]/div[13]/div/a[2]')
        if not next_link:
            next_link = tree.xpath('//*[@id="content"]/div[14]/div/a')        
            if next_link:
                if next_link[0].attrib["href"] == "search.php":
                    break
                if len(next_link) == 1 and "p=" in url:
                    break
            else:
                break
                
        url = next_link[-1].attrib["href"]
        url = "https://koe-koe.com/" + url;
        postlist += postlist_

    return postlist


def posturl_to_audiourl(url: str):
    OLD_POST_ID = 161299
    URL_POST_OLD = "https://file.koe-koe.com/sound/old/"
    URL_POST_UPLOAD = "https://file.koe-koe.com/sound/upload/"
    id = url.split("n=")[-1]
    if int(id) < OLD_POST_ID:
        audio_url = "{0}{1}.mp3".format(URL_POST_OLD,id)
    else:
        audio_url = "{0}{1}.mp3".format(URL_POST_UPLOAD,id)
    return audio_url
    

def download_voice(url: str, filepath: str, delay=0.5):

    ext = "." + url.split(".")[-1]
    filepath = str(pathlib.Path(filepath))+ext
    os.makedirs(pathlib.Path(filepath).parent, exist_ok=True)
    r = None
    try:
        time.sleep(delay)
        r = session.get(url=url, stream=True)
        r.raise_for_status()
        with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()
    except requests.HTTPError:
        if 500 <= r.status_code <= 599:
            raise KoekoeException_ServerError
        raise KoekoeException_NetworkError
    finally:
        if r:
            r.close()
    

def main():
    args = sys.argv
    
    if len(args) <= 1:
        print(A)
        print("URLがないです")
        return
    url = args[1]
    req_ex = requests.exceptions
    
    #url test
    try:
        urltest = get_html(url)
        if "detail.php" in url:
            print("対応していないURLです。")
            return
    except (req_ex.MissingSchema, req_ex.InvalidURL):
        print("不明なURL。https://から始まってますか？また、urlをシングルクォーテーションで囲ってみてください。")
        return
    except (KoekoeException_ServerError):
        print("サーバーエラーが返ってきたので終了します。あとでやり直してください。")
        return
    
    postlist = get_postlist(url)
    if not postlist:
        print("データを取得できませんでした。")
        return
    downloaded_list = []   
    postlist_len = len(postlist)
    i = 0
    try:
        for post in postlist:
            url_ = post["link"]
            username_ = post["username"]
            title_ = post["title"]
            date = post["date"]
            id = url_.split("n=")[-1]
            dlurl = posturl_to_audiourl(url_)
            
            if any(url_ in url for url in archive_list):
                postlist_len -= 1
                print("archive.txtによりスキップされました: {0}".format(url_))
                continue
            try:
                filename = "save/{0}/[{1}]{2}({3})".format(sanitize_filename(username_), id, sanitize_filename(title_), date)
                download_voice(dlurl, filename)
                print("保存({0}/{1}): {2}".format(i+1, postlist_len, url_))
                downloaded_list.append(url_)
            except KoekoeException_ServerError:
                raise
            except KoekoeException_Limiter:
                raise
            except Exception:
                print("保存に失敗しました。スキップします。: {0}".format(url_))
            i+=1

    except KoekoeException_ServerError:
        print("サーバーエラーが返ってきたので終了します。あとでやり直してください。")
        return
    except KoekoeException_Limiter:
        print("接続数の上限を超えました。")
        return
    except KoekoeException_NetworkError:
        print("サイトへの接続に連続で失敗しました。")
    finally:
        add_archive("\n".join(downloaded_list))
    
if __name__ == "__main__":
    main()
