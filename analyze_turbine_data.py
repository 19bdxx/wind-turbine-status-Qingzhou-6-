#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wind Turbine Status Analysis for Qingzhou 6 Unit (2025)
Comprehensive analysis of 74 wind turbines operational status data
"""

import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuration
DATA_DIR = "青州6机组运行状态-csv"
OUTPUT_DIR = "analysis_output"

# Status mapping (Chinese to English for processing)
STATUS_MAP = {
    '(5)发电状态': 'Power Generation',
    '(4)启机状态': 'Starting',
    '(3)待机状态': 'Standby',
    '(2)停机状态': 'Shutdown',
    '(1)停机过程': 'Stopping Process'
}

# Status codes
POWER_GEN_CODE = 5
SHUTDOWN_CODES = [1, 2]  # Stopping process and shutdown

def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

def parse_csv_file(filepath):
    """
    Parse a single CSV file and extract turbine operational data
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        DataFrame with parsed data or None if parsing fails
    """
    try:
        # Read CSV, skipping first 2 header rows
        df = pd.read_csv(filepath, skiprows=2, encoding='utf-8')
        
        # Get turbine ID from filename
        turbine_id = os.path.basename(filepath).replace('.csv', '')
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Extract relevant columns
        if '状态' in df.columns and '开始时间' in df.columns and '结束时间' in df.columns:
            df['turbine_id'] = turbine_id
            df['status'] = df['状态']
            df['status_code'] = df['状态码'] if '状态码' in df.columns else None
            df['start_time'] = pd.to_datetime(df['开始时间'], errors='coerce')
            df['end_time'] = pd.to_datetime(df['结束时间'], errors='coerce')
            df['duration_seconds'] = pd.to_numeric(df['持续时间(s)'], errors='coerce')
            df['duration_hours'] = pd.to_numeric(df['时长描述(h)'], errors='coerce')
            
            # Keep only necessary columns
            df = df[['turbine_id', 'status', 'status_code', 'start_time', 'end_time', 
                    'duration_seconds', 'duration_hours']].copy()
            
            # Remove rows with missing data
            df = df.dropna(subset=['status', 'start_time', 'end_time', 'duration_hours'])
            
            return df
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None

def load_all_data():
    """Load and combine all CSV files"""
    print("Loading data from all turbine CSV files...")
    
    csv_files = glob.glob(os.path.join(DATA_DIR, '*.csv'))
    csv_files = sorted(csv_files, key=lambda x: int(os.path.basename(x).replace('.csv', '')))
    
    all_data = []
    for filepath in csv_files:
        df = parse_csv_file(filepath)
        if df is not None and not df.empty:
            all_data.append(df)
    
    if not all_data:
        raise ValueError("No data loaded from CSV files")
    
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Loaded data from {len(all_data)} turbines")
    print(f"Total records: {len(combined_df)}")
    
    return combined_df

def calculate_basic_statistics(df):
    """
    Calculate basic statistics for each turbine
    Returns: DataFrame with statistics per turbine
    """
    print("\n=== Calculating Basic Statistics ===")
    
    stats_list = []
    
    for turbine_id in sorted(df['turbine_id'].unique(), key=lambda x: int(x)):
        turbine_data = df[df['turbine_id'] == turbine_id]
        
        # Total hours in dataset
        total_hours = turbine_data['duration_hours'].sum()
        
        # Statistics by status
        status_stats = {}
        for status in turbine_data['status'].unique():
            status_hours = turbine_data[turbine_data['status'] == status]['duration_hours'].sum()
            status_stats[status] = {
                'hours': status_hours,
                'percentage': (status_hours / total_hours * 100) if total_hours > 0 else 0
            }
        
        # Power generation hours
        power_gen_hours = turbine_data[turbine_data['status_code'] == 5]['duration_hours'].sum()
        
        # Shutdown hours (codes 1 and 2)
        shutdown_hours = turbine_data[turbine_data['status_code'].isin([1, 2])]['duration_hours'].sum()
        
        # Status transitions
        transitions = len(turbine_data) - 1
        
        # Power generation utilization rate
        utilization_rate = (power_gen_hours / total_hours * 100) if total_hours > 0 else 0
        
        stats_list.append({
            'turbine_id': turbine_id,
            'total_hours': total_hours,
            'power_gen_hours': power_gen_hours,
            'power_gen_percentage': utilization_rate,
            'shutdown_hours': shutdown_hours,
            'shutdown_percentage': (shutdown_hours / total_hours * 100) if total_hours > 0 else 0,
            'status_transitions': transitions,
            'records_count': len(turbine_data)
        })
    
    stats_df = pd.DataFrame(stats_list)
    
    # Sort by turbine ID
    stats_df['turbine_id_num'] = stats_df['turbine_id'].astype(int)
    stats_df = stats_df.sort_values('turbine_id_num').drop('turbine_id_num', axis=1)
    
    print(f"Processed statistics for {len(stats_df)} turbines")
    
    return stats_df

def analyze_anomalies(df):
    """
    Identify anomalies:
    1. Long shutdown events (>100 hours)
    2. Frequent start-stop units (>100 transitions/month)
    3. Zero power generation units
    """
    print("\n=== Analyzing Anomalies ===")
    
    # 1. Long shutdown events (>100 hours)
    long_shutdowns = df[
        (df['status_code'].isin([1, 2])) & 
        (df['duration_hours'] > 100)
    ].copy()
    long_shutdowns = long_shutdowns.sort_values('duration_hours', ascending=False)
    
    print(f"Found {len(long_shutdowns)} long shutdown events (>100 hours)")
    
    # 2. Frequent start-stop analysis (by month)
    df['month'] = df['start_time'].dt.to_period('M')
    
    monthly_transitions = df.groupby(['turbine_id', 'month']).size().reset_index(name='transitions')
    frequent_startups = monthly_transitions[monthly_transitions['transitions'] > 100]
    
    print(f"Found {len(frequent_startups)} turbine-month combinations with >100 state transitions")
    
    # 3. Zero power generation units
    power_gen_by_turbine = df[df['status_code'] == 5].groupby('turbine_id')['duration_hours'].sum()
    all_turbines = df['turbine_id'].unique()
    zero_gen_turbines = [t for t in all_turbines if t not in power_gen_by_turbine.index or power_gen_by_turbine[t] == 0]
    
    print(f"Found {len(zero_gen_turbines)} turbines with zero power generation")
    
    return {
        'long_shutdowns': long_shutdowns,
        'frequent_startups': frequent_startups,
        'zero_gen_turbines': zero_gen_turbines
    }

def analyze_trends(df):
    """
    Analyze trends:
    1. Monthly power generation efficiency
    2. Seasonal characteristics
    3. Equipment health score
    """
    print("\n=== Analyzing Trends ===")
    
    # 1. Monthly power generation efficiency
    df['month'] = df['start_time'].dt.to_period('M')
    
    monthly_stats = []
    for month in sorted(df['month'].unique()):
        month_data = df[df['month'] == month]
        
        total_hours = month_data['duration_hours'].sum()
        power_gen_hours = month_data[month_data['status_code'] == 5]['duration_hours'].sum()
        
        monthly_stats.append({
            'month': str(month),
            'total_hours': total_hours,
            'power_gen_hours': power_gen_hours,
            'efficiency': (power_gen_hours / total_hours * 100) if total_hours > 0 else 0,
            'active_turbines': month_data['turbine_id'].nunique()
        })
    
    monthly_df = pd.DataFrame(monthly_stats)
    print(f"Calculated monthly trends for {len(monthly_df)} months")
    
    # 2. Seasonal analysis
    def get_season(month_str):
        month_num = int(month_str.split('-')[1])
        if month_num in [12, 1, 2]:
            return 'Winter'
        elif month_num in [3, 4, 5]:
            return 'Spring'
        elif month_num in [6, 7, 8]:
            return 'Summer'
        else:
            return 'Autumn'
    
    df['season'] = df['month'].astype(str).apply(get_season)
    
    seasonal_stats = []
    for season in ['Spring', 'Summer', 'Autumn', 'Winter']:
        season_data = df[df['season'] == season]
        if not season_data.empty:
            total_hours = season_data['duration_hours'].sum()
            power_gen_hours = season_data[season_data['status_code'] == 5]['duration_hours'].sum()
            
            seasonal_stats.append({
                'season': season,
                'total_hours': total_hours,
                'power_gen_hours': power_gen_hours,
                'efficiency': (power_gen_hours / total_hours * 100) if total_hours > 0 else 0
            })
    
    seasonal_df = pd.DataFrame(seasonal_stats)
    print(f"Calculated seasonal trends for {len(seasonal_df)} seasons")
    
    # 3. Equipment health score (based on shutdown frequency and duration)
    health_scores = []
    
    for turbine_id in df['turbine_id'].unique():
        turbine_data = df[df['turbine_id'] == turbine_id]
        
        # Calculate metrics
        total_hours = turbine_data['duration_hours'].sum()
        shutdown_hours = turbine_data[turbine_data['status_code'].isin([1, 2])]['duration_hours'].sum()
        transitions = len(turbine_data)
        
        # Shutdown ratio (lower is better)
        shutdown_ratio = shutdown_hours / total_hours if total_hours > 0 else 1
        
        # Transition frequency per day (lower is better, normalized)
        days_in_year = 335  # 2025-01-01 to 2025-12-01
        transition_freq = transitions / days_in_year
        
        # Health score (0-100, higher is better)
        # Base score starts at 100
        score = 100
        # Deduct based on shutdown ratio (up to 50 points)
        score -= shutdown_ratio * 50
        # Deduct based on high transition frequency (up to 30 points)
        # Normal frequency is around 1-2 per day, excessive is >3
        if transition_freq > 3:
            score -= min((transition_freq - 3) * 2, 30)
        
        # Ensure score is between 0 and 100
        score = max(0, min(100, score))
        
        health_scores.append({
            'turbine_id': turbine_id,
            'health_score': round(score, 2),
            'shutdown_ratio': round(shutdown_ratio * 100, 2),
            'avg_daily_transitions': round(transition_freq, 2)
        })
    
    health_df = pd.DataFrame(health_scores)
    health_df['turbine_id_num'] = health_df['turbine_id'].astype(int)
    health_df = health_df.sort_values('turbine_id_num').drop('turbine_id_num', axis=1)
    
    print(f"Calculated health scores for {len(health_df)} turbines")
    
    return {
        'monthly': monthly_df,
        'seasonal': seasonal_df,
        'health': health_df
    }

def comparative_analysis(stats_df, health_df):
    """
    Perform comparative analysis:
    1. Cross-compare performance
    2. Identify TOP 10 best/worst
    3. Same model comparison (all are GW252/13600)
    """
    print("\n=== Performing Comparative Analysis ===")
    
    # Merge stats with health scores
    comparison_df = stats_df.merge(health_df, on='turbine_id')
    
    # Sort by power generation percentage (descending)
    comparison_df = comparison_df.sort_values('power_gen_percentage', ascending=False)
    
    # Top 10 best performing
    top_10_best = comparison_df.head(10)[['turbine_id', 'power_gen_percentage', 
                                           'health_score', 'status_transitions']].copy()
    
    # Top 10 worst performing
    top_10_worst = comparison_df.tail(10)[['turbine_id', 'power_gen_percentage', 
                                            'health_score', 'status_transitions']].copy()
    
    print(f"Identified TOP 10 best and worst performing turbines")
    
    # Overall statistics
    avg_power_gen = comparison_df['power_gen_percentage'].mean()
    avg_health = comparison_df['health_score'].mean()
    
    print(f"Average power generation: {avg_power_gen:.2f}%")
    print(f"Average health score: {avg_health:.2f}")
    
    return {
        'full_comparison': comparison_df,
        'top_10_best': top_10_best,
        'top_10_worst': top_10_worst,
        'avg_power_gen': avg_power_gen,
        'avg_health': avg_health
    }

def save_summary_tables(stats_df, anomalies, trends, comparison):
    """Save summary tables to CSV files"""
    print("\n=== Saving Summary Tables ===")
    
    ensure_output_dir()
    
    # 1. Basic statistics summary
    stats_df.to_csv(os.path.join(OUTPUT_DIR, 'turbine_basic_statistics.csv'), 
                    index=False, encoding='utf-8-sig')
    print("Saved: turbine_basic_statistics.csv")
    
    # 2. Long shutdown events
    if not anomalies['long_shutdowns'].empty:
        anomalies['long_shutdowns'][['turbine_id', 'status', 'start_time', 'end_time', 
                                      'duration_hours']].to_csv(
            os.path.join(OUTPUT_DIR, 'long_shutdown_events.csv'), 
            index=False, encoding='utf-8-sig')
        print("Saved: long_shutdown_events.csv")
    
    # 3. Frequent start-stop events
    if not anomalies['frequent_startups'].empty:
        anomalies['frequent_startups'].to_csv(
            os.path.join(OUTPUT_DIR, 'frequent_startups.csv'), 
            index=False, encoding='utf-8-sig')
        print("Saved: frequent_startups.csv")
    
    # 4. Monthly trends
    trends['monthly'].to_csv(os.path.join(OUTPUT_DIR, 'monthly_trends.csv'), 
                             index=False, encoding='utf-8-sig')
    print("Saved: monthly_trends.csv")
    
    # 5. Seasonal analysis
    trends['seasonal'].to_csv(os.path.join(OUTPUT_DIR, 'seasonal_analysis.csv'), 
                              index=False, encoding='utf-8-sig')
    print("Saved: seasonal_analysis.csv")
    
    # 6. Health scores
    trends['health'].to_csv(os.path.join(OUTPUT_DIR, 'equipment_health_scores.csv'), 
                            index=False, encoding='utf-8-sig')
    print("Saved: equipment_health_scores.csv")
    
    # 7. Full comparison
    comparison['full_comparison'].to_csv(os.path.join(OUTPUT_DIR, 'full_comparison.csv'), 
                                         index=False, encoding='utf-8-sig')
    print("Saved: full_comparison.csv")
    
    # 8. Top performers
    comparison['top_10_best'].to_csv(os.path.join(OUTPUT_DIR, 'top_10_best_turbines.csv'), 
                                     index=False, encoding='utf-8-sig')
    comparison['top_10_worst'].to_csv(os.path.join(OUTPUT_DIR, 'top_10_worst_turbines.csv'), 
                                      index=False, encoding='utf-8-sig')
    print("Saved: top_10_best_turbines.csv and top_10_worst_turbines.csv")

def generate_report(stats_df, anomalies, trends, comparison):
    """Generate comprehensive markdown analysis report"""
    print("\n=== Generating Analysis Report ===")
    
    report = []
    
    # Header
    report.append("# 青州6机组运行状态年度综合分析报告 (2025)")
    report.append("")
    report.append(f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("---")
    report.append("")
    
    # Executive Summary
    report.append("## 📊 执行摘要")
    report.append("")
    report.append(f"- **分析期间**: 2025年1月1日 至 2025年12月1日")
    report.append(f"- **机组数量**: {len(stats_df)} 台风机")
    report.append(f"- **平均发电利用率**: {comparison['avg_power_gen']:.2f}%")
    report.append(f"- **平均设备健康度**: {comparison['avg_health']:.2f}/100")
    report.append(f"- **异常停机事件**: {len(anomalies['long_shutdowns'])} 次 (>100小时)")
    report.append("")
    report.append("---")
    report.append("")
    
    # 1. Basic Statistics
    report.append("## 1️⃣ 基础统计分析")
    report.append("")
    report.append("### 1.1 整体运行情况")
    report.append("")
    total_power_gen = stats_df['power_gen_hours'].sum()
    total_hours = stats_df['total_hours'].sum()
    avg_utilization = (total_power_gen / total_hours * 100) if total_hours > 0 else 0
    report.append(f"- 总运行时长: {total_hours:,.2f} 小时")
    report.append(f"- 总发电时长: {total_power_gen:,.2f} 小时")
    report.append(f"- 整体发电利用率: **{avg_utilization:.2f}%**")
    report.append("")
    
    report.append("### 1.2 状态转换统计")
    report.append("")
    total_transitions = stats_df['status_transitions'].sum()
    avg_transitions = stats_df['status_transitions'].mean()
    report.append(f"- 总状态转换次数: {total_transitions:,} 次")
    report.append(f"- 平均每台机组转换次数: {avg_transitions:.2f} 次")
    report.append("")
    
    report.append("### 1.3 发电利用率分布")
    report.append("")
    report.append("| 利用率范围 | 机组数量 | 占比 |")
    report.append("|-----------|---------|------|")
    
    ranges = [(90, 100), (80, 90), (70, 80), (60, 70), (0, 60)]
    for low, high in ranges:
        count = len(stats_df[(stats_df['power_gen_percentage'] >= low) & 
                             (stats_df['power_gen_percentage'] < high)])
        pct = (count / len(stats_df) * 100) if len(stats_df) > 0 else 0
        report.append(f"| {low}% - {high}% | {count} | {pct:.1f}% |")
    
    report.append("")
    report.append("详细数据请参考: `analysis_output/turbine_basic_statistics.csv`")
    report.append("")
    report.append("---")
    report.append("")
    
    # 2. Anomaly Analysis
    report.append("## 2️⃣ 异常分析")
    report.append("")
    
    report.append("### 2.1 超长停机事件 (>100小时)")
    report.append("")
    if not anomalies['long_shutdowns'].empty:
        report.append(f"共发现 **{len(anomalies['long_shutdowns'])}** 次超长停机事件")
        report.append("")
        report.append("**TOP 10 最长停机事件**:")
        report.append("")
        report.append("| 机组编号 | 开始时间 | 结束时间 | 持续时长(小时) |")
        report.append("|---------|---------|---------|---------------|")
        
        for _, row in anomalies['long_shutdowns'].head(10).iterrows():
            report.append(f"| {row['turbine_id']} | {row['start_time']} | {row['end_time']} | {row['duration_hours']:.2f} |")
        
        report.append("")
        report.append("详细数据请参考: `analysis_output/long_shutdown_events.csv`")
    else:
        report.append("✅ 未发现超长停机事件")
    report.append("")
    
    report.append("### 2.2 频繁启停机组 (>100次/月)")
    report.append("")
    if not anomalies['frequent_startups'].empty:
        report.append(f"共发现 **{len(anomalies['frequent_startups'])}** 个机组-月份组合存在频繁启停")
        report.append("")
        report.append("**部分示例**:")
        report.append("")
        report.append("| 机组编号 | 月份 | 状态转换次数 |")
        report.append("|---------|------|-------------|")
        
        for _, row in anomalies['frequent_startups'].head(10).iterrows():
            report.append(f"| {row['turbine_id']} | {row['month']} | {row['transitions']} |")
        
        report.append("")
        report.append("详细数据请参考: `analysis_output/frequent_startups.csv`")
    else:
        report.append("✅ 未发现频繁启停异常")
    report.append("")
    
    report.append("### 2.3 零发电机组")
    report.append("")
    if anomalies['zero_gen_turbines']:
        report.append(f"共发现 **{len(anomalies['zero_gen_turbines'])}** 台机组零发电:")
        report.append("")
        report.append(f"机组编号: {', '.join(anomalies['zero_gen_turbines'])}")
    else:
        report.append("✅ 所有机组均有发电记录")
    report.append("")
    report.append("---")
    report.append("")
    
    # 3. Trend Analysis
    report.append("## 3️⃣ 趋势分析")
    report.append("")
    
    report.append("### 3.1 月度发电效率曲线")
    report.append("")
    report.append("| 月份 | 发电时长(小时) | 总时长(小时) | 发电效率 | 活跃机组数 |")
    report.append("|------|---------------|-------------|---------|-----------|")
    
    for _, row in trends['monthly'].iterrows():
        report.append(f"| {row['month']} | {row['power_gen_hours']:.2f} | {row['total_hours']:.2f} | {row['efficiency']:.2f}% | {row['active_turbines']} |")
    
    report.append("")
    report.append("详细数据请参考: `analysis_output/monthly_trends.csv`")
    report.append("")
    
    report.append("### 3.2 季节性运行特征")
    report.append("")
    report.append("| 季节 | 发电时长(小时) | 总时长(小时) | 发电效率 |")
    report.append("|------|---------------|-------------|---------|")
    
    season_order = ['Spring', 'Summer', 'Autumn', 'Winter']
    season_names = {'Spring': '春季', 'Summer': '夏季', 'Autumn': '秋季', 'Winter': '冬季'}
    
    for season in season_order:
        season_data = trends['seasonal'][trends['seasonal']['season'] == season]
        if not season_data.empty:
            row = season_data.iloc[0]
            report.append(f"| {season_names[season]} | {row['power_gen_hours']:.2f} | {row['total_hours']:.2f} | {row['efficiency']:.2f}% |")
    
    report.append("")
    report.append("详细数据请参考: `analysis_output/seasonal_analysis.csv`")
    report.append("")
    
    report.append("### 3.3 设备健康度评分")
    report.append("")
    avg_health = trends['health']['health_score'].mean()
    report.append(f"- 平均健康度评分: **{avg_health:.2f}/100**")
    report.append("")
    report.append("**健康度评分分布**:")
    report.append("")
    report.append("| 评分范围 | 机组数量 | 占比 |")
    report.append("|---------|---------|------|")
    
    health_ranges = [(90, 100), (80, 90), (70, 80), (60, 70), (0, 60)]
    for low, high in health_ranges:
        count = len(trends['health'][(trends['health']['health_score'] >= low) & 
                                     (trends['health']['health_score'] < high)])
        pct = (count / len(trends['health']) * 100) if len(trends['health']) > 0 else 0
        report.append(f"| {low} - {high} | {count} | {pct:.1f}% |")
    
    report.append("")
    report.append("详细数据请参考: `analysis_output/equipment_health_scores.csv`")
    report.append("")
    report.append("---")
    report.append("")
    
    # 4. Comparative Analysis
    report.append("## 4️⃣ 对比分析")
    report.append("")
    
    report.append("### 4.1 TOP 10 最佳性能机组")
    report.append("")
    report.append("| 排名 | 机组编号 | 发电利用率 | 健康度评分 | 状态转换次数 |")
    report.append("|-----|---------|-----------|-----------|-------------|")
    
    for idx, (_, row) in enumerate(comparison['top_10_best'].iterrows(), 1):
        report.append(f"| {idx} | {row['turbine_id']} | {row['power_gen_percentage']:.2f}% | {row['health_score']:.2f} | {row['status_transitions']} |")
    
    report.append("")
    report.append("详细数据请参考: `analysis_output/top_10_best_turbines.csv`")
    report.append("")
    
    report.append("### 4.2 TOP 10 待改进机组")
    report.append("")
    report.append("| 排名 | 机组编号 | 发电利用率 | 健康度评分 | 状态转换次数 |")
    report.append("|-----|---------|-----------|-----------|-------------|")
    
    for idx, (_, row) in enumerate(comparison['top_10_worst'].iterrows(), 1):
        report.append(f"| {idx} | {row['turbine_id']} | {row['power_gen_percentage']:.2f}% | {row['health_score']:.2f} | {row['status_transitions']} |")
    
    report.append("")
    report.append("详细数据请参考: `analysis_output/top_10_worst_turbines.csv`")
    report.append("")
    
    report.append("### 4.3 机型一致性分析")
    report.append("")
    report.append("所有74台机组型号均为 **GW252/13600**")
    report.append("")
    std_dev = stats_df['power_gen_percentage'].std()
    report.append(f"- 发电利用率标准差: {std_dev:.2f}%")
    report.append(f"- 最大发电利用率: {stats_df['power_gen_percentage'].max():.2f}%")
    report.append(f"- 最小发电利用率: {stats_df['power_gen_percentage'].min():.2f}%")
    report.append(f"- 利用率差值: {stats_df['power_gen_percentage'].max() - stats_df['power_gen_percentage'].min():.2f}%")
    report.append("")
    report.append("详细对比数据请参考: `analysis_output/full_comparison.csv`")
    report.append("")
    report.append("---")
    report.append("")
    
    # Key Findings
    report.append("## 🔍 核心发现")
    report.append("")
    report.append("1. **发电效率表现**")
    report.append(f"   - 整体发电利用率为 {avg_utilization:.2f}%，处于{'良好' if avg_utilization > 70 else '中等' if avg_utilization > 50 else '较低'}水平")
    report.append(f"   - 最优机组和最差机组发电利用率差异达 {stats_df['power_gen_percentage'].max() - stats_df['power_gen_percentage'].min():.2f}%，存在较大优化空间")
    report.append("")
    
    report.append("2. **异常事件概况**")
    if not anomalies['long_shutdowns'].empty:
        max_shutdown = anomalies['long_shutdowns']['duration_hours'].max()
        report.append(f"   - 最长停机事件持续 {max_shutdown:.2f} 小时，需重点关注")
    if not anomalies['frequent_startups'].empty:
        max_transitions = anomalies['frequent_startups']['transitions'].max()
        report.append(f"   - 部分机组单月状态转换高达 {max_transitions} 次，可能存在控制系统问题")
    if anomalies['zero_gen_turbines']:
        report.append(f"   - {len(anomalies['zero_gen_turbines'])} 台机组零发电，需紧急排查")
    report.append("")
    
    report.append("3. **季节性特征**")
    if not trends['seasonal'].empty:
        best_season = trends['seasonal'].loc[trends['seasonal']['efficiency'].idxmax(), 'season']
        worst_season = trends['seasonal'].loc[trends['seasonal']['efficiency'].idxmin(), 'season']
        season_names_report = {'Spring': '春季', 'Summer': '夏季', 'Autumn': '秋季', 'Winter': '冬季'}
        report.append(f"   - 发电效率最高季节: {season_names_report.get(best_season, best_season)}")
        report.append(f"   - 发电效率最低季节: {season_names_report.get(worst_season, worst_season)}")
    report.append("")
    
    report.append("4. **设备健康状况**")
    report.append(f"   - 平均健康度评分 {avg_health:.2f}/100")
    low_health_count = len(trends['health'][trends['health']['health_score'] < 70])
    if low_health_count > 0:
        report.append(f"   - {low_health_count} 台机组健康度评分低于70，建议加强维护")
    report.append("")
    report.append("---")
    report.append("")
    
    # Recommendations
    report.append("## 💡 运维优化建议")
    report.append("")
    report.append("### 短期措施 (1-3个月)")
    report.append("")
    report.append("1. **零发电机组处理**")
    if anomalies['zero_gen_turbines']:
        report.append(f"   - 立即排查机组 {', '.join(anomalies['zero_gen_turbines'][:5])} 等零发电设备")
        report.append("   - 检查电气系统、控制系统和机械部件")
    else:
        report.append("   - ✅ 当前无零发电机组")
    report.append("")
    
    report.append("2. **超长停机事件跟进**")
    if not anomalies['long_shutdowns'].empty:
        affected_turbines = anomalies['long_shutdowns']['turbine_id'].unique()[:5]
        report.append(f"   - 重点关注机组 {', '.join(affected_turbines)} 的停机原因")
        report.append("   - 建立停机预警机制，及时响应异常停机")
    report.append("")
    
    report.append("3. **频繁启停优化**")
    if not anomalies['frequent_startups'].empty:
        report.append("   - 检查控制系统参数设置，避免不必要的启停")
        report.append("   - 优化风速阈值和延时设置")
    report.append("")
    
    report.append("### 中长期措施 (3-12个月)")
    report.append("")
    report.append("1. **性能对标提升**")
    report.append("   - 以TOP 10机组为标杆，分析其运行策略")
    report.append("   - 将成功经验推广至表现较差的机组")
    report.append("")
    
    report.append("2. **预防性维护计划**")
    report.append(f"   - 对健康度评分低于70的 {low_health_count} 台机组制定专项维护方案")
    report.append("   - 建立基于数据的预测性维护体系")
    report.append("")
    
    report.append("3. **季节性运维策略**")
    report.append("   - 根据季节性特征调整维护计划")
    report.append("   - 在低效季节加强设备检查和优化")
    report.append("")
    
    report.append("4. **持续监控优化**")
    report.append("   - 建立实时监控仪表板，跟踪关键KPI")
    report.append("   - 定期（季度/月度）生成分析报告，持续改进")
    report.append("")
    report.append("---")
    report.append("")
    
    # Data Sources
    report.append("## 📂 数据文件索引")
    report.append("")
    report.append("所有详细数据表已保存至 `analysis_output/` 目录:")
    report.append("")
    report.append("1. `turbine_basic_statistics.csv` - 机组基础统计数据")
    report.append("2. `long_shutdown_events.csv` - 超长停机事件明细")
    report.append("3. `frequent_startups.csv` - 频繁启停记录")
    report.append("4. `monthly_trends.csv` - 月度趋势数据")
    report.append("5. `seasonal_analysis.csv` - 季节性分析")
    report.append("6. `equipment_health_scores.csv` - 设备健康度评分")
    report.append("7. `full_comparison.csv` - 机组全面对比")
    report.append("8. `top_10_best_turbines.csv` - TOP 10最佳机组")
    report.append("9. `top_10_worst_turbines.csv` - TOP 10待改进机组")
    report.append("")
    report.append("---")
    report.append("")
    
    # Footer
    report.append("## 📝 报告说明")
    report.append("")
    report.append("- **数据来源**: 青州6机组运行状态-csv/ 目录 (1.csv ~ 74.csv)")
    report.append("- **分析工具**: Python 数据分析脚本")
    report.append("- **分析周期**: 2025年1月1日 至 2025年12月1日")
    report.append("- **机组型号**: GW252/13600 (共74台)")
    report.append("")
    report.append("---")
    report.append("")
    report.append("*报告结束*")
    
    # Write to file
    report_content = '\n'.join(report)
    with open('ANALYSIS_REPORT.md', 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print("Generated: ANALYSIS_REPORT.md")
    
    return report_content

def main():
    """Main execution function"""
    print("=" * 70)
    print("Wind Turbine Status Analysis - Qingzhou 6 Unit (2025)")
    print("=" * 70)
    
    try:
        # Load data
        df = load_all_data()
        
        # Basic statistics
        stats_df = calculate_basic_statistics(df)
        
        # Anomaly analysis
        anomalies = analyze_anomalies(df)
        
        # Trend analysis
        trends = analyze_trends(df)
        
        # Comparative analysis
        comparison = comparative_analysis(stats_df, trends['health'])
        
        # Save summary tables
        save_summary_tables(stats_df, anomalies, trends, comparison)
        
        # Generate report
        generate_report(stats_df, anomalies, trends, comparison)
        
        print("\n" + "=" * 70)
        print("✅ Analysis completed successfully!")
        print("=" * 70)
        print("\nGenerated files:")
        print("  - ANALYSIS_REPORT.md (主报告)")
        print("  - analysis_output/ (详细数据表)")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
