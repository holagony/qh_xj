'''
关键因子-风速
'''
import pandas as pd
from sklearn.linear_model import LinearRegression
from Utils.config import cfg
from Utils.get_local_data import get_local_data
# from Report.code.Module02.wind import wind_report

def key_wind_statistics(df_main, df_sub):
    result = {}
    concat = pd.concat([df_main, df_sub], axis=0)
    concat['Mon'] = concat.index.month
    concat['Year'] = concat.index.year
    yearly_max = concat.dropna(subset=['WIN_S_Max']).groupby(['Station_Id_C', 'Year'])['WIN_S_Max'].max().reset_index()
    yearly_max.columns = ['站号', '年份', '最大风速(m/s)']
    yearly_max = yearly_max.pivot(index='年份', columns='站号', values='最大风速(m/s)')
    yearly_max = yearly_max.reindex(columns=sorted(yearly_max.columns)).reset_index(drop=False)
    
    yearly_inst = concat.dropna(subset=['WIN_S_Inst_Max']).groupby(['Station_Id_C', 'Year'])['WIN_S_Inst_Max'].max().reset_index()
    yearly_inst.columns = ['站号', '年份', '极大风速(m/s)']
    yearly_inst = yearly_inst.pivot(index='年份', columns='站号', values='极大风速(m/s)')
    yearly_inst = yearly_inst.reindex(columns=sorted(yearly_inst.columns)).reset_index(drop=False)

    monthly_avg_max = concat.dropna(subset=['WIN_S_Max']).groupby(['Station_Id_C', 'Mon'])['WIN_S_Max'].mean().round(1).reset_index()
    monthly_avg_max = monthly_avg_max.pivot(index='Station_Id_C', columns='Mon', values='WIN_S_Max')
    monthly_avg_max = monthly_avg_max.reindex(columns=sorted(monthly_avg_max.columns)).reset_index()
    monthly_avg_max.columns = ['站号'] + [str(c)+'月' for c in monthly_avg_max.columns[1:]]

    monthly_avg_inst = concat.dropna(subset=['WIN_S_Inst_Max']).groupby(['Station_Id_C', 'Mon'])['WIN_S_Inst_Max'].mean().round(1).reset_index()
    monthly_avg_inst = monthly_avg_inst.pivot(index='Station_Id_C', columns='Mon', values='WIN_S_Inst_Max')
    monthly_avg_inst = monthly_avg_inst.reindex(columns=sorted(monthly_avg_inst.columns)).reset_index()
    monthly_avg_inst.columns = ['站号'] + [str(c)+'月' for c in monthly_avg_inst.columns[1:]]
    
    def linreg_params(df):
        res = []
        years = df['年份'].values.reshape(-1, 1)
        for col in df.columns:
            if col == '年份':
                continue
            y = df[col].values
            m = ~pd.isna(y)
            x = years[m]
            y = y[m]
            if len(x) >= 2:
                model = LinearRegression()
                model.fit(x, y)
                slope = float(model.coef_[0])
                intercept = float(model.intercept_)
                r2 = float(model.score(x, y))
            else:
                slope = float('nan')
                intercept = float('nan')
                r2 = float('nan')
            res.append([col, slope, intercept, r2])
        return pd.DataFrame(res, columns=['站号', 'weight', 'bias', 'R_square'])
    yearly_max_lr = linreg_params(yearly_max).round(2)
    yearly_inst_lr = linreg_params(yearly_inst).round(2)

    result['历年最大风速'] = yearly_max
    result['历年极大风速'] = yearly_inst
    result['累年各月平均最大风速'] = monthly_avg_max
    result['累年各月平均极大风速'] = monthly_avg_inst
    result['最大风速拟合'] = yearly_max_lr
    result['极大风速拟合'] = yearly_inst_lr
    
    return result


if __name__ == '__main__':
    daily_df = pd.read_csv(r'C:/Users/mjynj/Desktop/qh_day.csv')
    sta_ids = '52866,52713'
    years = '2000,2020'

    daily_elements = 'WIN_S_Max,WIN_S_Inst_Max,'
    day_eles = ('Station_Name,Station_Id_C,Lat,Lon,Datetime,Year,Mon,Day,' + daily_elements[:-1]).split(',')
    post_daily_df = get_local_data(daily_df, sta_ids, day_eles, years, 'Day')
    
    df_main = post_daily_df[post_daily_df['Station_Id_C'] == '52866']
    df_sub = post_daily_df[post_daily_df['Station_Id_C'] == '52713']
    result = key_wind_statistics(df_main, df_sub)
