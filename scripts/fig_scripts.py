def plot_timeseries(ndvi_ts, gcc_ts):
    """Return a base64-encoded PNG of NDVI time series."""
    if ndvi_ts.empty or gcc_ts.empty:
        return None
    fig, ax = plt.subplots(figsize=(4, 3))
    
    ndvi_ts["date"] = pd.to_datetime(ndvi_ts["date"])
    
    """
    ndvi_ts['year'] = ndvi_ts['date'].dt.year
    ndvi_ts['month'] = ndvi_ts['date'].dt.month
    monthly_median_ndvi_ts=(
        ndvi_ts.groupby(['year', 'month'])['NDVI']
            .median()
            .reset_index()
    )
    monthly_median_ndvi_ts["year_month"]=pd.to_datetime(monthly_median_ndvi_ts[['year', 'month']].assign(DAY=1))
    """
    
    rolling_ndvi_ts=ndvi_ts.rolling("14D", on="date").median()
    
    gcc_ts['Date'] = pd.to_datetime(gcc_ts['Date'])    
    gcc_ts_roi=gcc_ts.groupby("Date").first().reset_index()

    #Pivot tables for plotting
    pivot_p90 = gcc_ts_roi.pivot(index='Date', columns='ROI', values='GCC_90p')
    pivot_mean = gcc_ts_roi.pivot(index='Date', columns='ROI', values='GCC_mean')    
    
    for roi in pivot_p90.columns:
        ax.plot(pivot_p90.index, pivot_p90[roi], linestyle='-', linewidth=1.5, label="GCC")

    
    
    ax.plot(rolling_ndvi_ts["date"], rolling_ndvi_ts["NDVI"], linestyle="-", linewidth=1.5, label="NDVI")
    ax.set_title("GCC and NDVI Timeseries", fontsize=10)
    ax.set_xlabel("Date")
    ax.set_ylabel("NDVI/GCC")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()    

def plot_plotly_timeseries(ndvi_ts, gcc_ts):
    
    import pandas as pd
    import plotly as ply
    import plotly.express as px
    import plotly.graph_objects as go


    if ndvi_ts.empty or gcc_ts.empty:
        return None
        
    ndvi_ts["date"] = pd.to_datetime(ndvi_ts["date"])

    rolling_ndvi_ts=ndvi_ts.rolling("14D", on="date").median()
    
    gcc_ts['Date'] = pd.to_datetime(gcc_ts['Date'])    
    gcc_ts_roi=gcc_ts.groupby("Date").first().reset_index()

    #Pivot tables for plotting
    pivot_p90 = gcc_ts_roi.pivot(index='Date', columns='ROI', values='GCC_90p')
    pivot_mean = gcc_ts_roi.pivot(index='Date', columns='ROI', values='GCC_mean')    

    fig=go.Figure()


    fig.add_trace(go.Scatter(x=rolling_ndvi_ts["date"], y=rolling_ndvi_ts["NDVI"], name="NDVI"))

    for roi in pivot_p90.columns:
        fig.add_trace(go.Scatter(x=pivot_p90.index, y=pivot_p90[roi], name="GCC"))


    fig.update_layout(autosize=False, width=450)
    fig_html=fig.to_html(include_plotlyjs="cdn", full_html=False)

    return fig_html
