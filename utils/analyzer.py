import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import LabelEncoder
from typing import Dict, List, Any


class DataAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.issues = []
        self.quality_score = 100

    def analyze(self) -> Dict[str, Any]:
        self._check_missing_values()
        self._check_duplicates()
        self._check_outliers()
        self._check_data_types()
        self._check_class_imbalance()
        self._check_high_correlation()
        self._check_constant_columns()
        
        return {
            'quality_score': max(0, self.quality_score),
            'issues': self.issues,
            'total_issues': len(self.issues)
        }
    
    def _add_issue(self, severity: str, category: str, title: str, description: str, columns: List[str] = None):
        score_impact = {'critical': 20, 'warning': 10, 'info': 5}
        self.quality_score -= score_impact.get(severity, 0)
        
        self.issues.append({
            'severity': severity,
            'category': category,
            'title': title,
            'description': description,
            'columns': columns or []
        })

    def _check_missing_values(self):
        missing = self.df.isnull().sum()
        for col in missing[missing > 0].index:
            pct = (missing[col] / len(self.df)) * 100
            
            if pct > 50:
                severity = 'critical'
                desc = f"{pct:.1f}% missing - Consider dropping this column"
            elif pct > 20:
                severity = 'warning'
                desc = f"{pct:.1f}% missing - Needs imputation strategy"
            else:
                severity = 'info'
                desc = f"{pct:.1f}% missing - Minor issue"
            
            self._add_issue(severity, 'Missing Values', f"Column '{col}' has missing data", desc, [col])
    
    def _check_duplicates(self):
        dup_count = self.df.duplicated().sum()
        if dup_count > 0:
            pct = (dup_count / len(self.df)) * 100
            severity = 'critical' if pct > 5 else 'warning'
            self._add_issue(severity, 'Duplicates', f"{dup_count} duplicate rows found", 
                          f"{pct:.1f}% of dataset - May bias model training")
    
    def _check_outliers(self):
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            data = self.df[col].dropna()
            if len(data) < 10:
                continue
                
            z_scores = np.abs(stats.zscore(data))
            outliers = (z_scores > 3).sum()
            
            if outliers > 0:
                pct = (outliers / len(data)) * 100
                if pct > 10:
                    severity = 'warning'
                else:
                    severity = 'info'
                    
                self._add_issue(severity, 'Outliers', f"Column '{col}' has {outliers} outliers",
                              f"{pct:.1f}% extreme values (|z-score| > 3)", [col])
    
    def _check_data_types(self):
        for col in self.df.columns:
            if self.df[col].dtype == 'object':
                try:
                    pd.to_numeric(self.df[col].dropna())
                    self._add_issue('warning', 'Data Types', f"Column '{col}' should be numeric",
                                  "Stored as text but contains numeric values", [col])
                except:
                    pass
    
    def _check_class_imbalance(self):
        for col in self.df.columns:
            if self.df[col].nunique() < 10 and self.df[col].nunique() > 1:
                value_counts = self.df[col].value_counts()
                ratio = value_counts.max() / value_counts.min()
                
                if ratio > 10:
                    severity = 'critical' if ratio > 50 else 'warning'
                    self._add_issue(severity, 'Class Imbalance', f"Column '{col}' is imbalanced",
                                  f"Max/min ratio: {ratio:.1f}x - May need resampling", [col])
    
    def _check_high_correlation(self):
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return
            
        corr_matrix = self.df[numeric_cols].corr().abs()
        upper_triangle = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        
        high_corr = [(col, row, upper_triangle.loc[row, col]) 
                     for col in upper_triangle.columns 
                     for row in upper_triangle.index 
                     if upper_triangle.loc[row, col] > 0.95]
        
        for col1, col2, corr_val in high_corr:
            self._add_issue('warning', 'High Correlation', 
                          f"Columns '{col1}' and '{col2}' highly correlated",
                          f"Correlation: {corr_val:.3f} - May cause multicollinearity", [col1, col2])
    
    def _check_constant_columns(self):
        for col in self.df.columns:
            if self.df[col].nunique() == 1:
                self._add_issue('warning', 'Constant Column', f"Column '{col}' has only one value",
                              "Zero variance - Provides no information", [col])