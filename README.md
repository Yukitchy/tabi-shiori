# tabi-shiori — 家族・友だち向けの旅のしおり（箱）
`packs/<slug>/trip.json` と `img/` を置いて `python3 engine/build.py <slug>` → `docs/<slug>/index.html`。
GitHub Pages（/docs）で公開。1画面ずつスナップで進む縦長ページ。

## アルバム（写真・動画）
`python3 engine/album.py <slug> <iPhone書き出しフォルダ>` で jpg/png/heic/mov/mp4 を
`packs/<slug>/album/` に縮小取り込み＋`album.json` 生成（撮影日時・GPSつき／再実行しても重複しない）。
キャプションは album.json の `cap` を手で書く。album.json があれば、しおりに日別グリッド＋Leaflet地図が付く。

## まとめページ
trip.json の `"with"`（yuri など）と `"dates"` を見て `python3 engine/build.py`（引数なし）が
`docs/yuri/index.html` を生成。行った旅／これからの旅は `dates[1]` と今日の比較で自動判定。
