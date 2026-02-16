#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple visualization generator for wind turbine analysis results
Creates basic text-based charts for quick insights
"""

import pandas as pd
import os

OUTPUT_DIR = "analysis_output"

def print_bar_chart(label, value, max_value, width=50):
    """Print a simple text-based bar chart"""
    bar_length = int((value / max_value) * width) if max_value > 0 else 0
    bar = '█' * bar_length
    print(f"{label:20s} {bar} {value:.2f}%")

def visualize_top_performers():
    """Visualize top performing turbines"""
    print("\n" + "="*70)
    print("TOP 10 BEST PERFORMING TURBINES - Power Generation Utilization")
    print("="*70)
    
    df = pd.read_csv(os.path.join(OUTPUT_DIR, 'top_10_best_turbines.csv'), encoding='utf-8-sig')
    max_val = df['power_gen_percentage'].max()
    
    for idx, row in df.iterrows():
        label = f"Turbine #{row['turbine_id']}"
        print_bar_chart(label, row['power_gen_percentage'], max_val)
    
    print("\n" + "="*70)
    print("TOP 10 WORST PERFORMING TURBINES - Power Generation Utilization")
    print("="*70)
    
    df_worst = pd.read_csv(os.path.join(OUTPUT_DIR, 'top_10_worst_turbines.csv'), encoding='utf-8-sig')
    
    for idx, row in df_worst.iterrows():
        label = f"Turbine #{row['turbine_id']}"
        print_bar_chart(label, row['power_gen_percentage'], max_val)

def visualize_monthly_trends():
    """Visualize monthly power generation efficiency"""
    print("\n" + "="*70)
    print("MONTHLY POWER GENERATION EFFICIENCY TRENDS")
    print("="*70)
    
    df = pd.read_csv(os.path.join(OUTPUT_DIR, 'monthly_trends.csv'), encoding='utf-8-sig')
    max_val = df['efficiency'].max()
    
    for _, row in df.iterrows():
        month = row['month']
        print_bar_chart(month, row['efficiency'], max_val, width=60)

def visualize_seasonal():
    """Visualize seasonal patterns"""
    print("\n" + "="*70)
    print("SEASONAL POWER GENERATION EFFICIENCY")
    print("="*70)
    
    df = pd.read_csv(os.path.join(OUTPUT_DIR, 'seasonal_analysis.csv'), encoding='utf-8-sig')
    max_val = df['efficiency'].max()
    
    season_names = {
        'Spring': '春季 (Spring)',
        'Summer': '夏季 (Summer)',
        'Autumn': '秋季 (Autumn)',
        'Winter': '冬季 (Winter)'
    }
    
    for _, row in df.iterrows():
        season = season_names.get(row['season'], row['season'])
        print_bar_chart(season, row['efficiency'], max_val, width=60)

def visualize_health_distribution():
    """Visualize health score distribution"""
    print("\n" + "="*70)
    print("EQUIPMENT HEALTH SCORE DISTRIBUTION")
    print("="*70)
    
    df = pd.read_csv(os.path.join(OUTPUT_DIR, 'equipment_health_scores.csv'), encoding='utf-8-sig')
    
    # Calculate distribution
    ranges = [
        (90, 100, "90-100 (Excellent)"),
        (80, 90, "80-90  (Good)"),
        (70, 80, "70-80  (Fair)"),
        (60, 70, "60-70  (Poor)"),
        (0, 60, "0-60   (Critical)")
    ]
    
    total = len(df)
    
    for low, high, label in ranges:
        count = len(df[(df['health_score'] >= low) & (df['health_score'] < high)])
        percentage = (count / total * 100) if total > 0 else 0
        print_bar_chart(label, percentage, 100, width=40)
        print(f"                     Count: {count}/{total} turbines")

def print_summary_statistics():
    """Print key summary statistics"""
    print("\n" + "="*70)
    print("KEY PERFORMANCE INDICATORS (KPI)")
    print("="*70)
    
    # Basic statistics
    stats = pd.read_csv(os.path.join(OUTPUT_DIR, 'turbine_basic_statistics.csv'), encoding='utf-8-sig')
    
    avg_power_gen = stats['power_gen_percentage'].mean()
    total_power_gen = stats['power_gen_hours'].sum()
    total_hours = stats['total_hours'].sum()
    
    print(f"\n📊 Overall Performance:")
    print(f"   • Average Power Generation Utilization: {avg_power_gen:.2f}%")
    print(f"   • Total Power Generation Hours: {total_power_gen:,.2f} hours")
    print(f"   • Total Operating Hours: {total_hours:,.2f} hours")
    print(f"   • Number of Turbines: {len(stats)}")
    
    # Anomalies
    long_shutdowns = pd.read_csv(os.path.join(OUTPUT_DIR, 'long_shutdown_events.csv'), encoding='utf-8-sig')
    frequent_startups = pd.read_csv(os.path.join(OUTPUT_DIR, 'frequent_startups.csv'), encoding='utf-8-sig')
    
    print(f"\n⚠️  Anomalies Detected:")
    print(f"   • Long Shutdown Events (>100h): {len(long_shutdowns)}")
    print(f"   • Frequent Start-Stop Instances: {len(frequent_startups)}")
    if not long_shutdowns.empty:
        max_shutdown = long_shutdowns['duration_hours'].max()
        print(f"   • Longest Shutdown Duration: {max_shutdown:.2f} hours")
    
    # Health scores
    health = pd.read_csv(os.path.join(OUTPUT_DIR, 'equipment_health_scores.csv'), encoding='utf-8-sig')
    avg_health = health['health_score'].mean()
    
    print(f"\n🏥 Equipment Health:")
    print(f"   • Average Health Score: {avg_health:.2f}/100")
    print(f"   • Turbines with Health < 70: {len(health[health['health_score'] < 70])}")
    print(f"   • Best Health Score: {health['health_score'].max():.2f}")
    print(f"   • Worst Health Score: {health['health_score'].min():.2f}")

def main():
    """Main visualization function"""
    print("="*70)
    print("WIND TURBINE ANALYSIS - VISUALIZATION SUMMARY")
    print("="*70)
    
    try:
        print_summary_statistics()
        visualize_monthly_trends()
        visualize_seasonal()
        visualize_top_performers()
        visualize_health_distribution()
        
        print("\n" + "="*70)
        print("✅ Visualization completed!")
        print("="*70)
        print("\nFor detailed data, please refer to:")
        print("  • ANALYSIS_REPORT.md")
        print("  • analysis_output/*.csv")
        print()
        
    except Exception as e:
        print(f"\n❌ Error during visualization: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
