A = ""
from lxml import html as html_
import requests
from bs4 import BeautifulSoup
import re
import time
from pathvalidate import sanitize_filename
import pathlib
import os
import sys
import rich
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
    else:
        raise KoekoeException_NetworkError
    return response.text

def get_postlist(url: str, limit = 100) -> list:
    
    limit_page = limit

    postlist = []
    for i in range(limit_page):
        print("ページ数: {0} URL: {1}".format(i+1, url))
        html = get_html(url)
        tree = html_.fromstring(html)
        soup = BeautifulSoup(html, "lxml")
        
        a_tag = soup.find_all("a", href=re.compile("detail"), title=re.compile("の投稿"))
        if a_tag:
            j = 0
            for a_tagtag in a_tag:
                if not j % 2 == 0:
                    # print(a_tagtag)
                    link = "https://koe-koe.com/"+a_tagtag["href"]
                    username = a_tagtag.text
                    title = a_tagtag["title"][1:-4]
                    postlist.append({"link": link, "username": username, "title": title})
                j+=1
        
        next_link = tree.xpath('//*[@id="content"]/div[13]/div/a[2]')
        url = ""

        if not next_link:
            next_link = tree.xpath('//*[@id="content"]/div[14]/div/a')
        
        if next_link:
            if next_link[0].attrib["href"] == "search.php":
                break
        else:
            break
        url = next_link[-1].attrib["href"]
        # if len(next_link) == 1:
        #     url = next_link[-1].attrib["href"]
        # elif len(next_link) == 2:
        #     url = next_link[-1].attrib["href"]
        # else:
        #     break
        url = "https://koe-koe.com/" + url;


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
        print("データを取得できませんでした。プログラムが壊れているか、不明なURLが指定された可能性があります。")
        return
    
    downloaded_list = []
    i = 0
    postlist_len = len(postlist)
    try:
        for post in postlist:
            url_ = post["link"]
            username_ = post["username"]
            title_ = post["title"]
            id = url_.split("n=")[-1]
            dlurl = posturl_to_audiourl(url_)
            
            if any(url_ in url for url in archive_list):
                postlist_len -= 1
                print("archive.txtによりスキップされました: {0}".format(url_))
                continue
            try:
                filename = "save/{0}/[{1}]{2}".format(sanitize_filename(username_), id, sanitize_filename(title_))
                download_voice(dlurl, filename)
            except KoekoeException_ServerError:
                raise
            except Exception:
                print("保存に失敗しました。スキップします。: {0}".format(url_))
            
            print("保存({0}/{1}): {2}".format(i+1, postlist_len, url_))
            downloaded_list.append(url_)
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
