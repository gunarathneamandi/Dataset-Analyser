from __future__ import annotations

from h2o_wave import ui, data
import pandas as pd
import numpy as np
from typing import List, Tuple

def create_distribution_plot(df: pd.DataFrame, column: str) -> ui.PlotCard:
    col_data = df[column].dropna()
    
    if pd.api.types.is_numeric_dtype(col_data):
        hist, bin_edges = np.histogram(col_data, bins=30)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        return ui.plot_card(
            box='',
            title=f'Distribution: {column}',
            data=data('x y', rows=[(float(x), int(y)) for x, y in zip(bin_centers, hist)]),
            plot=ui.plot([
                ui.mark(type='interval', x='=x', y='=y', y_min=0)
            ])
        )
    else:
        value_counts = col_data.value_counts().head(10)
        return ui.plot_card(
            box='',
            title=f'Top Values: {column}',
            data=data('category count', rows=[(str(k), int(v)) for k, v in value_counts.items()]),
            plot=ui.plot([
                ui.mark(type='interval', x='=category', y='=count', y_min=0)
            ])
        )

def create_correlation_heatmap(df: pd.DataFrame) -> ui.PlotCard:
    numeric_cols = df.select_dtypes(include=[np.number]).columns[:10]
    
    if len(numeric_cols) < 2:
        return None
    
    corr_matrix = df[numeric_cols].corr()
    
    rows = []
    for i, col1 in enumerate(corr_matrix.columns):
        for j, col2 in enumerate(corr_matrix.columns):
            rows.append((col1, col2, float(corr_matrix.iloc[i, j])))
    
    return ui.plot_card(
        box='',
        title='Correlation Heatmap',
        data=data('x y correlation', rows=rows),
        plot=ui.plot([
            ui.mark(
                type='polygon',
                x='=x',
                y='=y',
                color='=correlation',
                color_range='#fee8c8 #e34a33'
            )
        ])
    )

def create_quality_gauge(score: int) -> ui.StatCard:
    if score >= 80:
        caption = 'Excellent'
    elif score >= 60:
        caption = 'Good'
    elif score >= 40:
        caption = 'Fair'
    else:
        caption = 'Poor'
    # Build a simple, compatible card showing the quality score and a progress bar.
    return ui.form_card(
        box='',
        items=[
            ui.text_xl('Data Quality Score'),
            ui.text(f'{score} / 100 — {caption}'),
            ui.progress(label='', caption='', value=round(score / 100, 2))
        ]
    )

def create_issue_severity_chart(issues: List[dict]) -> ui.PlotCard:
    severity_counts = {'critical': 0, 'warning': 0, 'info': 0}
    
    for issue in issues:
        severity_counts[issue['severity']] += 1
    
    rows = [
        ('Critical', severity_counts['critical'], '#e74c3c'),
        ('Warning', severity_counts['warning'], '#f39c12'),
        ('Info', severity_counts['info'], '#3498db')
    ]
    
    return ui.plot_card(
        box='',
        title='Issues by Severity',
        data=data('severity count color', rows=rows),
        plot=ui.plot([
            ui.mark(type='interval', x='=severity', y='=count', y_min=0, color='=color')
        ])
    )

def create_column_quality_table(column_stats: pd.DataFrame) -> Tuple[List, List]:
    columns = [
        ui.table_column(name='column', label='Column', sortable=True),
        ui.table_column(name='dtype', label='Type', sortable=True),
        ui.table_column(name='missing_pct', label='Missing %', sortable=True),
        ui.table_column(name='unique', label='Unique', sortable=True),
    ]
    
    rows = []
    for _, row in column_stats.iterrows():
        rows.append(ui.table_row(
            name=str(row['column']),
            cells=[
                str(row['column']),
                str(row['dtype']),
                f"{row['missing_pct']:.1f}%",
                str(row['unique'])
            ]
        ))
    
    return columns, rows