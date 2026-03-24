import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta

from config import DATA_DIR

st.set_page_config(
    page_title="求人ボックス 週次レポート",
    page_icon="📊",
    layout="wide",
)

# --- カスタムCSS ---
st.markdown("""
<style>
    .main-header { font-size: 28px; font-weight: bold; margin-bottom: 0; }
    .sub-header { color: #9BA4B5; font-size: 14px; margin-bottom: 24px; }
    .kpi-card {
        background: #1E2130; border-radius: 10px; padding: 18px 20px; border: 1px solid #2D3250;
    }
    .kpi-label { color: #9BA4B5; font-size: 13px; margin-bottom: 4px; }
    .kpi-value { font-size: 28px; font-weight: bold; color: #FAFAFA; }
    .kpi-sub { font-size: 13px; margin-top: 4px; }
    .kpi-up { color: #4CAF50; }
    .kpi-down { color: #FF5252; }
    .kpi-neutral { color: #9BA4B5; }
    .kpi-value-green { color: #4CAF50; }
    .kpi-value-red { color: #FF5252; }
    .section-divider { border-top: 1px solid #2D3250; margin: 24px 0; }
</style>
""", unsafe_allow_html=True)

NUMERIC_COLUMNS = ["表示回数", "クリック数", "応募数", "アクション数", "平均クリック単価", "費用", "応募単価"]


@st.cache_data(ttl=60)
def load_all_data() -> pd.DataFrame:
    """data/ 配下の全CSVを読み込んで1つのDataFrameにまとめる。"""
    all_dfs = []

    if not DATA_DIR.exists():
        return pd.DataFrame()

    for day_dir in sorted(DATA_DIR.iterdir()):
        if not day_dir.is_dir():
            continue

        dir_name = day_dir.name

        # 新形式: YYYY-MM-DD（日次）
        if len(dir_name) == 10 and dir_name.count("-") == 2:
            data_date = dir_name
        # 旧形式: YYYY-MM-DD_YYYY-MM-DD（週次）- 互換性維持
        elif "_" in dir_name:
            data_date = dir_name.split("_")[0]
        else:
            continue

        for csv_file in day_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file, encoding="cp932")
            except UnicodeDecodeError:
                df = pd.read_csv(csv_file, encoding="utf-8")

            df["アカウント"] = csv_file.stem
            df["日付"] = data_date
            all_dfs.append(df)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)

    # 数値列の変換
    for col in NUMERIC_COLUMNS:
        if col in combined.columns:
            combined[col] = (
                combined[col].astype(str)
                .str.replace("\uffe5", "", regex=False)
                .str.replace("￥", "", regex=False)
                .str.replace(",", "", regex=False)
                .str.replace("%", "", regex=False)
                .replace({"": "0", "nan": "0"})
            )
            combined[col] = pd.to_numeric(combined[col], errors="coerce").fillna(0)

    combined["日付_dt"] = pd.to_datetime(combined["日付"])
    combined["週"] = combined["日付_dt"].dt.to_period("W").apply(lambda x: x.start_time.strftime("%Y-%m-%d"))
    combined["月"] = combined["日付_dt"].dt.to_period("M").astype(str)

    return combined


def render_kpi(label, value, sub_text="", value_color=""):
    color_class = f"kpi-value-{value_color}" if value_color else ""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {color_class}">{value}</div>
        <div class="kpi-sub">{sub_text}</div>
    </div>
    """, unsafe_allow_html=True)


def format_change(current, prev, is_currency=False, invert=False):
    if prev == 0:
        return '<span class="kpi-neutral">前期データなし</span>'
    change = ((current - prev) / prev) * 100
    is_good = change <= 0 if invert else change >= 0
    css_class = "kpi-up" if is_good else "kpi-down"
    prefix = "前期 ¥" if is_currency else "前期 "
    return f'<span class="{css_class}">前期比 {change:+.0f}%</span>　{prefix}{prev:,.0f}'


def aggregate_data(data: pd.DataFrame, period_col: str, selected_period: str, accounts: list) -> pd.DataFrame:
    """指定期間・アカウントでフィルタしたデータを返す。"""
    return data[(data[period_col] == selected_period) & (data["アカウント"].isin(accounts))]


def get_prev_period(periods: list, current: str) -> str | None:
    idx = periods.index(current)
    return periods[idx + 1] if idx + 1 < len(periods) else None


def main():
    data = load_all_data()

    if data.empty:
        st.warning("データがありません。main.py を実行してCSVをダウンロードしてください。")
        st.code("python main.py", language="bash")
        return

    # --- サイドバー ---
    st.sidebar.header("フィルタ")

    # 期間の切り口
    view_mode = st.sidebar.radio("表示期間", ["日次", "週次", "月次"])

    if view_mode == "日次":
        period_col = "日付"
    elif view_mode == "週次":
        period_col = "週"
    else:
        period_col = "月"

    periods = sorted(data[period_col].unique(), reverse=True)
    selected_period = st.sidebar.selectbox("期間を選択", periods, index=0)
    prev_period = get_prev_period(periods, selected_period)

    accounts = sorted(data["アカウント"].unique())
    selected_accounts = st.sidebar.multiselect("アカウント", accounts, default=accounts)

    # データ取得
    current = aggregate_data(data, period_col, selected_period, selected_accounts)
    prev = aggregate_data(data, period_col, prev_period, selected_accounts) if prev_period else pd.DataFrame()

    # 集計
    cur_impressions = current["表示回数"].sum()
    cur_clicks = current["クリック数"].sum()
    cur_apps = current["応募数"].sum()
    cur_cost = current["費用"].sum()
    cur_ctr = (cur_clicks / cur_impressions * 100) if cur_impressions > 0 else 0
    cur_cpc = (cur_cost / cur_clicks) if cur_clicks > 0 else 0
    cur_cpa = (cur_cost / cur_apps) if cur_apps > 0 else 0

    prev_impressions = prev["表示回数"].sum() if not prev.empty else 0
    prev_clicks = prev["クリック数"].sum() if not prev.empty else 0
    prev_apps = prev["応募数"].sum() if not prev.empty else 0
    prev_cost = prev["費用"].sum() if not prev.empty else 0
    prev_ctr = (prev_clicks / prev_impressions * 100) if prev_impressions > 0 else 0
    prev_cpc = (prev_cost / prev_clicks) if prev_clicks > 0 else 0
    prev_cpa = (prev_cost / prev_apps) if prev_apps > 0 else 0

    # ===== ヘッダー =====
    period_label = {"日次": "日次", "週次": "週次", "月次": "月次"}[view_mode]
    st.markdown(f'<div class="main-header">求人ボックス {period_label}レポート</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">集計期間: {selected_period}　|　{len(selected_accounts)} アカウント</div>',
        unsafe_allow_html=True,
    )

    # ===== KPIカード 上段 =====
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("公開中求人数", f"{len(current):,}件", f"{len(selected_accounts)} アカウント")
    with c2:
        render_kpi("総表示回数", f"{cur_impressions:,.0f}", format_change(cur_impressions, prev_impressions))
    with c3:
        render_kpi("総クリック数", f"{cur_clicks:,.0f}", format_change(cur_clicks, prev_clicks))
    with c4:
        ctr_color = "green" if cur_ctr >= prev_ctr else "red" if prev_ctr > 0 else ""
        render_kpi("平均CTR", f"{cur_ctr:.2f}%",
                   f'前期 {prev_ctr:.2f}%' if prev_ctr > 0 else "", value_color=ctr_color)

    st.markdown("")

    # ===== KPIカード 下段 =====
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        render_kpi("総費用", f"¥{cur_cost:,.0f}",
                   format_change(cur_cost, prev_cost, is_currency=True, invert=True))
    with c6:
        app_color = "green" if cur_apps >= prev_apps else "red" if prev_apps > 0 else ""
        render_kpi("総応募数", f"{cur_apps:,.0f}",
                   format_change(cur_apps, prev_apps), value_color=app_color)
    with c7:
        cpa_color = "green" if cur_cpa <= prev_cpa else "red" if prev_cpa > 0 else ""
        render_kpi("平均CPA", f"¥{cur_cpa:,.0f}",
                   f'前期 ¥{prev_cpa:,.0f}' if prev_cpa > 0 else "", value_color=cpa_color)
    with c8:
        render_kpi("平均CPC", f"¥{cur_cpc:,.0f}",
                   f'前期 ¥{prev_cpc:,.0f}' if prev_cpc > 0 else "")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ===== タブ =====
    tab1, tab2, tab3 = st.tabs(["推移グラフ", "アカウント別", "詳細データ"])

    # --- タブ1: 推移グラフ ---
    with tab1:
        # 期間ごとの推移（日次なら日ごと、週次なら週ごと、月次なら月ごと）
        trend_data = (
            data[data["アカウント"].isin(selected_accounts)]
            .groupby(period_col)
            .agg(表示回数=("表示回数", "sum"), クリック数=("クリック数", "sum"),
                 応募数=("応募数", "sum"), 費用=("費用", "sum"))
            .reset_index()
            .sort_values(period_col)
        )
        trend_data["CTR"] = (trend_data["クリック数"] / trend_data["表示回数"].replace(0, float("nan")) * 100).fillna(0)
        trend_data["CPA"] = (trend_data["費用"] / trend_data["応募数"].replace(0, float("nan"))).fillna(0)

        metric_options = ["表示回数", "クリック数", "応募数", "費用", "CTR", "CPA"]
        selected_metric = st.selectbox("指標を選択", metric_options)

        fig_trend = px.line(
            trend_data, x=period_col, y=selected_metric,
            title=f"{selected_metric}の推移（{period_label}）",
            markers=True, color_discrete_sequence=["#4FC3F7"],
        )
        fig_trend.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA", xaxis_title="", yaxis_title=selected_metric,
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # アカウント別比較（現在期間 vs 前期間）
        col_left, col_right = st.columns(2)

        with col_left:
            cur_by_acc = current.groupby("アカウント").agg(
                表示回数=("表示回数", "sum"), クリック数=("クリック数", "sum")).reset_index()
            cur_by_acc["CTR"] = (cur_by_acc["クリック数"] / cur_by_acc["表示回数"].replace(0, float("nan")) * 100).fillna(0)
            cur_by_acc["期間"] = "今期"

            if not prev.empty:
                prev_by_acc = prev.groupby("アカウント").agg(
                    表示回数=("表示回数", "sum"), クリック数=("クリック数", "sum")).reset_index()
                prev_by_acc["CTR"] = (prev_by_acc["クリック数"] / prev_by_acc["表示回数"].replace(0, float("nan")) * 100).fillna(0)
                prev_by_acc["期間"] = "前期"
                ctr_compare = pd.concat([cur_by_acc, prev_by_acc], ignore_index=True)
            else:
                ctr_compare = cur_by_acc

            fig_ctr = px.bar(ctr_compare, x="アカウント", y="CTR", color="期間", barmode="group",
                             title="アカウント別 CTR比較",
                             color_discrete_map={"今期": "#4FC3F7", "前期": "#37474F"})
            fig_ctr.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                  font_color="#FAFAFA", xaxis_tickangle=-45)
            st.plotly_chart(fig_ctr, use_container_width=True)

        with col_right:
            cur_apps_acc = current.groupby("アカウント")["応募数"].sum().reset_index()
            cur_apps_acc["期間"] = "今期"
            if not prev.empty:
                prev_apps_acc = prev.groupby("アカウント")["応募数"].sum().reset_index()
                prev_apps_acc["期間"] = "前期"
                apps_compare = pd.concat([cur_apps_acc, prev_apps_acc], ignore_index=True)
            else:
                apps_compare = cur_apps_acc

            fig_apps = px.bar(apps_compare, x="アカウント", y="応募数", color="期間", barmode="group",
                              title="アカウント別 応募数比較",
                              color_discrete_map={"今期": "#4CAF50", "前期": "#37474F"})
            fig_apps.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                   font_color="#FAFAFA", xaxis_tickangle=-45)
            st.plotly_chart(fig_apps, use_container_width=True)

    # --- タブ2: アカウント別 ---
    with tab2:
        account_summary = current.groupby("アカウント").agg(
            求人数=("求人番号", "count") if "求人番号" in current.columns else ("表示回数", "count"),
            表示回数=("表示回数", "sum"), クリック数=("クリック数", "sum"),
            応募数=("応募数", "sum"), 費用=("費用", "sum"),
        ).reset_index()

        account_summary["CTR"] = (account_summary["クリック数"] / account_summary["表示回数"].replace(0, float("nan")) * 100).fillna(0).round(2)
        account_summary["CPC"] = (account_summary["費用"] / account_summary["クリック数"].replace(0, float("nan"))).fillna(0).round(0)
        account_summary["CPA"] = (account_summary["費用"] / account_summary["応募数"].replace(0, float("nan"))).fillna(0).round(0)

        if not prev.empty:
            prev_summary = prev.groupby("アカウント").agg(
                前期_表示=("表示回数", "sum"), 前期_応募=("応募数", "sum")).reset_index()
            account_summary = account_summary.merge(prev_summary, on="アカウント", how="left").fillna(0)
            account_summary["表示_変化"] = ((account_summary["表示回数"] - account_summary["前期_表示"]) / account_summary["前期_表示"].replace(0, float("nan")) * 100).fillna(0).round(1)
            account_summary["応募_変化"] = ((account_summary["応募数"] - account_summary["前期_応募"]) / account_summary["前期_応募"].replace(0, float("nan")) * 100).fillna(0).round(1)

        display_cols = ["アカウント", "求人数", "表示回数", "クリック数", "CTR", "応募数", "費用", "CPC", "CPA"]
        if "表示_変化" in account_summary.columns:
            display_cols.extend(["表示_変化", "応募_変化"])

        st.dataframe(
            account_summary[display_cols].sort_values("費用", ascending=False),
            use_container_width=True,
            column_config={
                "CTR": st.column_config.NumberColumn(format="%.2f%%"),
                "CPC": st.column_config.NumberColumn(format="¥%.0f"),
                "CPA": st.column_config.NumberColumn(format="¥%.0f"),
                "費用": st.column_config.NumberColumn(format="¥%.0f"),
                "表示_変化": st.column_config.NumberColumn("表示 前期比", format="%+.1f%%"),
                "応募_変化": st.column_config.NumberColumn("応募 前期比", format="%+.1f%%"),
            },
            hide_index=True,
        )

        cpa_data = account_summary[account_summary["CPA"] > 0].sort_values("CPA", ascending=True)
        if not cpa_data.empty:
            fig_cpa = px.bar(cpa_data, x="CPA", y="アカウント", orientation="h",
                             title="アカウント別 CPA", color="CPA",
                             color_continuous_scale=["#4CAF50", "#FFB74D", "#FF5252"])
            fig_cpa.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                  font_color="#FAFAFA")
            st.plotly_chart(fig_cpa, use_container_width=True)

    # --- タブ3: 詳細データ ---
    with tab3:
        st.markdown("#### 求人別詳細データ")
        detail_account = st.selectbox("アカウントを選択", selected_accounts, key="detail_acc")
        detail_data = current[current["アカウント"] == detail_account].copy()

        detail_cols = ["求人番号", "求人タイトル", "勤務地", "ステータス", "表示回数", "クリック数", "応募数", "費用", "平均クリック単価", "応募単価"]
        available_cols = [c for c in detail_cols if c in detail_data.columns]

        st.dataframe(
            detail_data[available_cols].sort_values("費用", ascending=False),
            use_container_width=True,
            column_config={
                "費用": st.column_config.NumberColumn(format="¥%.0f"),
                "平均クリック単価": st.column_config.NumberColumn("CPC", format="¥%.0f"),
                "応募単価": st.column_config.NumberColumn("CPA", format="¥%.0f"),
            },
            hide_index=True, height=600,
        )


if __name__ == "__main__":
    main()
