"""
NEDOから取得した日射量データを変換するプログラム
@dededemio
"""
import os
import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import argparse

# コマンドライン引数を解析する
parser = argparse.ArgumentParser(description='Process some files.')
parser.add_argument('rad_hourly_csv_path', type=str, help='年間時別日射量データベース(METPV-20)のCSVファイルパス')
parser.add_argument('rad_monthly_csv_path', type=str, help='年間月別日平均日射量データベース(MONSOLA-20)のCSVファイルパス')
parser.add_argument('ICHIJO_data_folder_path', type=str, help='ICHIJO POWER MONITORから取得したCSVデータを格納したフォルダパス')
parser.add_argument('rad_act_folder_path', type=str, help='日射量計測データを格納したフォルダパス')
args = parser.parse_args()

print("""
STEP1-1 年間時別日射量データベース(METPV-20)のCSVデータを読み込み、使えるように処理
""")
# CSVファイルを読み込む
hourly_data = pd.read_csv(args.rad_hourly_csv_path, skiprows=1, header=None)

# 列名を設定する
column_names = [
    '0', '気象要素番号', '月', '日', '代表年', '1時', '2時', '3時', '4時', '5時', '6時', '7時', '8時',
    '9時', '10時', '11時', '12時', '13時', '14時', '15時', '16時', '17時', '18時', '19時',
    '20時', '21時', '22時', '23時', '24時', '最大', '最小', '積算', '平均', '行番号'
]
column_names = [column_name.replace('時', '') for column_name in column_names]
hourly_data.columns = column_names

# 不要な列を削除
hourly_data = hourly_data.drop(columns=['0', '気象要素番号', '代表年', '最大', '最小', '積算', '平均', '行番号'])

# 1時間ごとのデータに変換
hourly_data = pd.melt(hourly_data, id_vars=['月', '日'], var_name='時間', value_name='値')

# 日時をdatetime型に変換してソート
# 24時=翌日0時が含まれるのでto_datetime()で直接時刻まで変換できず、一度年月日のみ変換した後時刻を加算する
year = datetime.datetime.now().year # 現在年を取得
hourly_data['日付'] = hourly_data.apply(lambda row: f"{year}-{row['月']}-{row['日']}", axis=1) # 年月日を結合した列を作成
hourly_data['date'] = pd.to_datetime(hourly_data['日付']) # 年月日をdatetime型に変換
hourly_data['datetime'] = hourly_data['date']+pd.to_timedelta(hourly_data['時間'].astype(int), unit='h') # 時間を加算
# 日時をindexに設定してソート
hourly_data = hourly_data.set_index('datetime')
hourly_data = hourly_data.drop(columns=['月', '日', '時間', '日付', 'date']) # 不要な列を削除
hourly_data = hourly_data.sort_index() # ソート

# CSVは[0.01MJ/m2]のため、MJ/m2→kWh/m2に単位を換算する
hourly_data = hourly_data/100 # 0.01MJ/m2 -> MJ/m2
hourly_data_kWh = hourly_data/3.6 # MJ/m2 -> kWh/m2
hourly_data_kWh.columns = ['Global Solar Radiation[kWh/m2]']

print("""
STEP1-2 年間月別日射量データベース(MONSOLA-20)のCSVデータと比較
""")
# 月毎に積算し日平均値を計算
monthly_sum = hourly_data_kWh.resample('M').sum()
month_days = round(hourly_data_kWh.resample('M').size()/24)
monthly_avg = monthly_sum / month_days.values[:, None]
monthly_avg = monthly_avg.drop(monthly_avg.index[12])

# 月別日積算斜面日射量と比較（傾斜角10度）
monthly_ref = pd.read_csv(args.rad_monthly_csv_path)
monthly_ref = monthly_ref.set_index('月')
plt.figure()
plt.plot(range(1,13), monthly_avg, "o-", range(1,13), monthly_ref, "o-")
plt.grid()
plt.xlabel('Month')
plt.ylabel(monthly_avg.columns[0])
plt.legend(["Monthly data calculated from hourly data", "Monthly reference data"])
plt.savefig(os.path.join("./img","STEP1-2_Comparison of MONSOLA with METPV monthly totals.png"))

# 誤差の定量化
rad_rmse = np.sqrt( np.square(monthly_avg.values - monthly_ref.values).mean() ) # 平均平方二乗誤差(RMSE)0.157[kWh/m2]
rad_mape = np.abs((monthly_avg.values - monthly_ref.values)/monthly_ref.values).mean() # 平均絶対パーセント誤差(MAPE)3.57%
print("MONSOLA-20とMETPV-20の月別集計の誤差")
print("RMSE[kWh/m2], {0:0.3f}".format(rad_rmse))
print("MAPE[%]     , {0:0.3f}".format(rad_mape*100))


print("""
STEP2 時別太陽光発電量の予測計算
""")
# 損失係数
coef = {'Month': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        'Coefficient': [0.9, 0.9, 0.9, 0.85, 0.85, 0.8, 0.8, 0.8, 0.8, 0.85, 0.85, 0.9]}
coef_df = pd.DataFrame(coef)

# 太陽光発電効率
pv_cap = 8.5 # システム容量

# 発電量を以下の式で計算
# 単位面積あたり日射量 × 面積 × 太陽光発電効率 × 損失係数 = 単位面積当たり日射量 × システム容量 × 損失係数
hourly_data_kWh['Month'] = hourly_data_kWh.index.month
merged_df = hourly_data_kWh.merge(coef_df, on='Month', how='left')
merged_df['Power Generation[kWh]'] = merged_df['Global Solar Radiation[kWh/m2]'] * pv_cap * merged_df['Coefficient']
hourly_gen = merged_df['Power Generation[kWh]']
hourly_gen.index = hourly_data_kWh.index
monthly_sum_gen = hourly_gen.resample('M').sum()

print("""
STEP3-1 月別太陽光発電量の予実比較
""")
# 電力実績データを収集
def read_power_data(data_dir):
    files = os.listdir(data_dir)
    dfs = []
    for file in files:
        if ".csv" not in file: # csvファイルだけ読み取り対象とする
            continue
        df = pd.read_csv(os.path.join(data_dir,file), index_col=0, parse_dates=True, encoding="utf-8-sig")
        dfs.append(df)
    merged_df = pd.concat(dfs)
    merged_df = merged_df[~merged_df.index.duplicated(keep='first')]
    return merged_df
act_df = read_power_data(args.ICHIJO_data_folder_path)
act_df.index = act_df.index + pd.to_timedelta(1, unit='h') # ICHIJO POWER MONITORのデータは0:00=0時台のデータなので、+1時間して、過去1時間の積算値に直す

# 月別日射量データを比較
monthly_sum_act =act_df.resample('M').sum()
plt.figure()
plt.plot(range(3,10), monthly_sum_gen[2:9], "o-", range(3,10), monthly_sum_act['発電'][1:8], "o-")
plt.grid()
plt.xlabel('Month')
plt.ylabel(hourly_gen.name)
plt.legend(["Predicted data", "Actual data"])
plt.savefig(os.path.join("./img","STEP3-1_Comparison of predicted and actual PV power generation(monthly).png"))

print("""
STEP3-2 時別太陽光発電量の予実比較
""")
# 3-9の各月で時別最大発電量と日別発電量が最も近い日の時別発電量を比較
for month in range(3,10):
    # 近似日を特定(RMSEが最も小さい日)
    pred = hourly_gen[hourly_gen.index.month==month]
    act = act_df[act_df.index.month==month]['発電']
    rmse = np.sqrt(np.square(pred-act).resample('D').mean())
    min_day = rmse.idxmin().date()
    #mape = np.abs(((pred-act)/(act+0.00001)).resample('D').mean()) # RMSEではなくMAPEを使う場合
    #min_day = mape.idxmin().date()
    # 近似日のデータを描画
    pred = hourly_gen[hourly_gen.index.date==min_day]
    act = act_df[act_df.index.date==min_day]['発電']
    plt.figure()
    plt.plot(range(0,24), pred, "o-", range(0,24), act, "o-")
    plt.grid()
    plt.xlabel('Hour')
    plt.ylabel(hourly_gen.name)
    plt.legend(["Predicted data", "Actual data"])
    plt.title('PV power generation on ' + str(min_day))
    plt.savefig(os.path.join("./img","STEP3-2_Comparison of predicted and actual PV power generation("+str(min_day)+").png"))
    
print("""
STEP4 日射量データを代表年と今年で比較し、その影響を予測値に反映して月別データを再度比較
""")
# 代表年と今年のデータを集約
dir = args.rad_act_folder_path
files = os.listdir(dir)
rad_act_data = pd.DataFrame()
for file in files:
    if "csv" in file:
        df = pd.read_csv(os.path.join(dir, file), skiprows=3, index_col=0, encoding="cp932")
        rad_act_data = pd.concat([rad_act_data, df])
rad_act_data.index = pd.to_datetime(rad_act_data.index)
# 代表年データを抽出
rad_rep_year = rad_act_data[rad_act_data.index.year < 2023]
rad_rep_year.index = [x.replace(year=2020) for x in rad_rep_year.index] # 年が異なってソートしにくいので統一
rad_rep_year = rad_rep_year.sort_index()
monthly_rep_year = rad_rep_year['日射量(MJ/㎡)'].resample('M').sum()
# 今年以降のデータを抽出
rad_this_year = rad_act_data[rad_act_data.index.year >= 2023]
monthly_this_year = rad_this_year['日射量(MJ/㎡)'].resample('M').sum()

# 2023と代表年の(東京の)日射量の差をプロット
plt.figure()
plt.plot(range(3,10), monthly_this_year[2:9],"o-", range(3,10), monthly_rep_year[2:9], "o-")
plt.grid()
plt.xlabel('Month')
plt.ylabel("Solar radiation[MJ/m2]")
plt.legend(["2023", "Representative year"])
plt.title("Total solar radiation in Tokyo")
plt.savefig(os.path.join("./img","STEP4_Total solar radiation in Tokyo.png"))

# 日射量補正値を計算し、月別発電量を補正
rad_adj = monthly_this_year[2:9].values / monthly_rep_year[2:9].values # 補正値
monthly_sum_gen_adj = monthly_sum_gen[2:9] * rad_adj # 補正した予測発電量
plt.figure()
plt.plot(range(3,10), monthly_sum_gen[2:9], "o-", range(3,10), monthly_sum_gen_adj, "o-g", range(3,10), monthly_sum_act['発電'][1:8], "o-")
plt.grid()
plt.xlabel('Month')
plt.ylabel(hourly_gen.name)
plt.legend(["Predicted data(unadjusted)", "Predicted data(adjusted)", "Actual data"])
plt.savefig(os.path.join("./img","STEP4_Comparison of predicted and actual PV power generation(monthly adjusted).png"))

# 誤差の定量化
gen_rmse     = np.sqrt( np.square(monthly_sum_gen[2:9].values - monthly_sum_act['発電'][1:8].values).mean() ) # 平均平方二乗誤差(RMSE)103.7[kWh/m2]
gen_mape     = np.abs((monthly_sum_gen[2:9].values - monthly_sum_act['発電'][1:8].values)/monthly_sum_act['発電'][1:8].values).mean() # 平均絶対パーセント誤差(MAPE)7.30%
gen_rmse_adj = np.sqrt( np.square(monthly_sum_gen_adj.values - monthly_sum_act['発電'][1:8].values).mean() ) # 平均平方二乗誤差(RMSE)56.6[kWh/m2]
gen_mape_adj = np.abs((monthly_sum_gen_adj.values - monthly_sum_act['発電'][1:8].values)/monthly_sum_act['発電'][1:8].values).mean() # 平均絶対パーセント誤差(MAPE)4.27%
print("補正前後の太陽光発電量の予測と実績のRMSEとMAPE")
print("指標, 補正前, 補正後")
print("RMSE[kWh], {0:0.3f}, {1:0.3f}".format(gen_rmse, gen_rmse_adj))
print("MAPE[%]  , {0:0.3f}, {1:0.3f}".format(gen_mape*100, gen_mape_adj*100))

