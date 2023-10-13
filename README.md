# PV_power_prediction
以下の記事に記載した太陽光発電量の予測と実績値の比較計算をするスクリプト
* [【一条工務店i-smile】太陽光発電量の予測と実績（2023年3～9月） - 白旗製作所](https://dededemio.hatenablog.jp/entry/2023/10/13/111829)

# 使用方法
* PV_power_prediction.pyに以下の引数をつけて実行する
  - rad_hourly_csv_path: 年間時別日射量データベース(METPV-20)からダウンロードしたCSVファイルパス
  - rad_monthly_csv_path: 年間月別日平均日射量データベース(MONSOLA-20)の年間日射量データを記載したCSVファイルパス
  - ICHIJO_data_folder_path: ICHIJO POWER MONITORから取得したCSVデータを格納したフォルダパス
  - rad_act_folder_path: 気象庁HPからダウンロードした日射量データCSVを格納したフォルダパス
* PV_power_prediction.cmdを参照

# 動作環境
* Windows 11 Pro 22H2
* Python 3.9.13

# ライセンス
* MITライセンス