import pandas as pd
from typing import Tuple, Optional

def load_dataset(file_path: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            return None, "Unsupported file format. Use CSV or Excel."
        
        if df.empty:
            return None, "Dataset is empty"
        
        return df, None
    except Exception as e:
        return None, f"Error loading file: {str(e)}"
    

def get_dataset_info(df: pd.DataFrame) -> dict:
    info = {
        'rows': len(df),
        'columns': len(df.columns),
        'memory_usage': df.memory_usage(deep=True).sum() /1024**2,
        'column_types': df.dtypes.value_counts().to_dict(),
        'missing_values': df.isnull().sum().sum(),
        # Backwards-compatibility: some callers expect `missing_total` key
        'missing_total': int(df.isnull().sum().sum()),
        'duplicate_rows': df.duplicated().sum()
    }
    return info

def get_column_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats = []
    for col in df.columns:
        col_info = {
            'column': col,
            'dtype': str(df[col].dtype),
            'missing': df[col].isnull().sum(),
            'missing_pct': round(df[col].isnull().sum() / len(df) * 100, 2),
            'unique': df[col].nunique(),
            'unique_pct': round(df[col].nunique() / len(df) * 100, 2)
        }
        
        if pd.api.types.is_numeric_dtype(df[col]):
            col_info.update({
                'mean': round(df[col].mean(), 2) if df[col].notna().any() else None,
                'std': round(df[col].std(), 2) if df[col].notna().any() else None,
                'min': df[col].min() if df[col].notna().any() else None,
                'max': df[col].max() if df[col].notna().any() else None
            })
        
        stats.append(col_info)
    
    return pd.DataFrame(stats)




