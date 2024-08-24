# koekoedownloader
https://koe-koe.com の音声をダウンロードするツール
```
pip install -r requirements.txt


# 検索画面のURLをそのまま入れて実行

python koekoe.py "https://koe-koe.com/tag_list.php?tag=BL"

python koekoe.py "https://koe-koe.com/search.php?word=名無し&g=2&m=1"

python koekoe.py "https://koe-koe.com/search.php?g=0&sort=1&word=ねこ"


# 数が多い場合はストッパーがかかるので時間を置いて再度実行

python koekoe.py "https://koe-koe.com/tag_list.php?tag=BL"
接続数の上限を超えました。

python koekoe.py "https://koe-koe.com/tag_list.php?tag=BL"
```
