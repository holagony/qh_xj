'''
关键因子-积雪深度
'''
import pandas as pd
from sklearn.linear_model import LinearRegression


def key_snow_statistics(df_main, df_sub):
    result = {}
    concat = pd.concat([df_main, df_sub], axis=0)
    concat['Mon'] = concat.index.month
    concat['Year'] = concat.index.year

    yearly = concat.dropna(subset=['Snow_Depth']).groupby(['Station_Id_C', 'Year'])['Snow_Depth'].max().reset_index()
    yearly.columns = ['站号', '年份', '最大日积雪深度(cm)']
    yearly = yearly.pivot(index='年份', columns='站号', values='最大日积雪深度(cm)')
    yearly = yearly.reindex(columns=sorted(yearly.columns)).reset_index(drop=False)

    monthly = concat.dropna(subset=['Snow_Depth']).groupby(['Station_Id_C', 'Mon'])['Snow_Depth'].mean().round(1).reset_index()
    monthly = monthly.pivot(index='Station_Id_C', columns='Mon', values='Snow_Depth')
    monthly = monthly.reindex(columns=sorted(monthly.columns)).reset_index()
    monthly.columns = ['站号'] + [str(c) + '月' for c in monthly.columns[1:]]

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

    yearly_lr = linreg_params(yearly).round(2)

    result['历年最大积雪深度'] = yearly
    result['累年各月平均积雪深度'] = monthly
    result['最大积雪深度拟合'] = yearly_lr

    return result
