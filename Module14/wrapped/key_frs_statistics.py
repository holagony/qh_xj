'''
关键因子-冻土深度
'''
import pandas as pd
from sklearn.linear_model import LinearRegression


def key_frs_statistics(daily_df):
    result = {}
    daily_df['Mon'] = daily_df.index.month
    daily_df['Year'] = daily_df.index.year
    cols = [c for c in ['FRS_1st_Bot', 'FRS_2nd_Bot'] if c in daily_df.columns]
    daily_df['frs'] = daily_df[cols].max(axis=1)

    yearly = daily_df.dropna(subset=['frs']).groupby(['Station_Id_C', 'Year'])['frs'].max().reset_index()
    yearly.columns = ['站号', '年份', '最大日冻土深度(cm)']
    yearly = yearly.pivot(index='年份', columns='站号', values='最大日冻土深度(cm)')
    yearly = yearly.reindex(columns=sorted(yearly.columns)).reset_index(drop=False)

    monthly = daily_df.dropna(subset=['frs']).groupby(['Station_Id_C', 'Mon'])['frs'].mean().round(1).reset_index()
    monthly = monthly.pivot(index='Station_Id_C', columns='Mon', values='frs')
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

    result['历年最大冻土深度'] = yearly
    result['累年各月平均冻土深度'] = monthly
    result['最大冻土深度拟合'] = yearly_lr

    return result
