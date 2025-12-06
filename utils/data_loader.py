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
        'duplicate_rows': df.duplicated().sum()
    }
    return info





