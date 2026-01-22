'''
关键因子-极端气温
'''
import pandas as pd
from sklearn.linear_model import LinearRegression


def key_tem_statistics(df_main, df_sub):
    result = {}
    concat = pd.concat([df_main, df_sub], axis=0)
    concat['Mon'] = concat.index.month
    concat['Year'] = concat.index.year

    yearly_max = concat.dropna(subset=['TEM_Max']).groupby(['Station_Id_C', 'Year'])['TEM_Max'].max().reset_index()
    yearly_max.columns = ['站号', '年份', '极端最高气温(°C)']
    yearly_max = yearly_max.pivot(index='年份', columns='站号', values='极端最高气温(°C)')
    yearly_max = yearly_max.reindex(columns=sorted(yearly_max.columns)).reset_index(drop=False)

    yearly_min = concat.dropna(subset=['TEM_Min']).groupby(['Station_Id_C', 'Year'])['TEM_Min'].min().reset_index()
    yearly_min.columns = ['站号', '年份', '极端最低气温(°C)']
    yearly_min = yearly_min.pivot(index='年份', columns='站号', values='极端最低气温(°C)')
    yearly_min = yearly_min.reindex(columns=sorted(yearly_min.columns)).reset_index(drop=False)

    monthly_avg_max = concat.dropna(subset=['TEM_Max']).groupby(['Station_Id_C', 'Mon'])['TEM_Max'].mean().round(1).reset_index()
    monthly_avg_max = monthly_avg_max.pivot(index='Station_Id_C', columns='Mon', values='TEM_Max')
    monthly_avg_max = monthly_avg_max.reindex(columns=sorted(monthly_avg_max.columns)).reset_index()
    monthly_avg_max.columns = ['站号'] + [str(c) + '月' for c in monthly_avg_max.columns[1:]]

    monthly_avg_min = concat.dropna(subset=['TEM_Min']).groupby(['Station_Id_C', 'Mon'])['TEM_Min'].mean().round(1).reset_index()
    monthly_avg_min = monthly_avg_min.pivot(index='Station_Id_C', columns='Mon', values='TEM_Min')
    monthly_avg_min = monthly_avg_min.reindex(columns=sorted(monthly_avg_min.columns)).reset_index()
    monthly_avg_min.columns = ['站号'] + [str(c) + '月' for c in monthly_avg_min.columns[1:]]

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
    yearly_min_lr = linreg_params(yearly_min).round(2)

    result['历年最高气温'] = yearly_max
    result['历年最低气温'] = yearly_min
    result['累年各月平均最高气温'] = monthly_avg_max
    result['累年各月平均最低气温'] = monthly_avg_min
    result['最高气温拟合'] = yearly_max_lr
    result['最低气温拟合'] = yearly_min_lr

    return result
