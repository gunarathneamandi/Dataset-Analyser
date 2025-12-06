import json
import google.generativeai as genai
from typing import Dict, List, Any
import pandas as pd
import os

class AIEngine:
    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    def generate_insights(self, df: pd.DataFrame, issues: List[Dict]) -> str:
        try:
            prompt = self._build_insight_prompt(df, issues)
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating insights: {str(e)}"
    
    def suggest_fixes(self, issue: Dict, df_sample: pd.DataFrame) -> str:
        try:
            prompt = self._build_fix_prompt(issue, df_sample)
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating fix suggestions: {str(e)}"
    
    def generate_executive_summary(self, quality_score: int, issues: List[Dict], df_info: Dict) -> str:
        try:
            prompt = self._build_summary_prompt(quality_score, issues, df_info)
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def _build_insight_prompt(self, df: pd.DataFrame, issues: List[Dict]) -> str:
        sample_data = df.head(5).to_string()
        dtypes = df.dtypes.to_string()
        
        prompt = f"""Analyze this dataset and provide 3-5 key insights about data quality issues.

            Dataset Shape: {df.shape[0]} rows × {df.shape[1]} columns

            Data Types:
            {dtypes}

            Sample Data:
            {sample_data}

            Detected Issues ({len(issues)} total):
            {json.dumps(issues[:3], indent=2)}

            Provide insights about:
            1. Most critical data quality problems
            2. Potential impact on machine learning models
            3. Hidden patterns or risks

            Be concise and technical. Focus on actionable insights."""

        return prompt
    
    def _build_fix_prompt(self, issue: Dict, df_sample: pd.DataFrame) -> str:
        columns_info = ""
        if issue.get('columns'):
            for col in issue['columns'][:2]:
                if col in df_sample.columns:
                    sample_values = df_sample[col].head(5).tolist()
                    columns_info += f"\n{col}: {sample_values}"
        
        prompt = f"""Suggest a specific fix for this data quality issue.

            Issue:
            - Severity: {issue.get('severity')}
            - Category: {issue.get('category')}
            - Title: {issue.get('title')}
            - Description: {issue.get('description')}

            Sample Data:{columns_info}

            Provide:
            1. Recommended fix (1-2 sentences)
            2. Why this approach (1 sentence)
            3. Alternative option if applicable

            Be specific and practical."""

        return prompt
    
    def _build_summary_prompt(self, quality_score: int, issues: List[Dict], df_info: Dict) -> str:
        critical = sum(1 for i in issues if i.get('severity') == 'critical')
        warnings = sum(1 for i in issues if i.get('severity') == 'warning')
        info = sum(1 for i in issues if i.get('severity') == 'info')
        
        prompt = f"""Generate a concise executive summary for a dataset quality analysis.

            Dataset Info:
            - Rows: {df_info.get('rows', 0):,}
            - Columns: {df_info.get('columns', 0)}
            - Quality Score: {quality_score}/100
            - Total Issues: {len(issues)}

            Issues Breakdown:
            - Critical: {critical}
            - Warnings: {warnings}
            - Info: {info}

            Write a 3-4 sentence executive summary highlighting:
            1. Overall data quality assessment
            2. Most critical issues
            3. Recommended next steps

            Keep it business-focused and actionable."""

        return prompt