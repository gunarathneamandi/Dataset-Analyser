from h2o_wave import main, app, Q, ui, data
import os
import re
import asyncio
from utils import load_dataset, get_dataset_info, get_column_stats, DataAnalyzer, AIEngine
from utils.visualizer import (
    create_distribution_plot, 
    create_correlation_heatmap, 
    create_quality_gauge,
    create_issue_severity_chart,
    create_column_quality_table
)

UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _generate_quick_fix(issue: dict) -> str:
    """Return a short, deterministic fix suggestion for an issue without calling AI.

    Keeps responses fast by using rule-based templates based on category/severity.
    """
    category = (issue.get('category') or '').lower()
    cols = issue.get('columns') or []
    col_part = f" for column '{cols[0]}'" if cols else ''

    if 'missing' in category or 'missing values' in category:
        return f"Impute or remove missing values{col_part}. For >50% missing consider dropping the column; otherwise use mean/median (numeric) or mode/explicit placeholder (categorical)."
    if 'duplicates' in category:
        return "Deduplicate rows (drop exact duplicates) and investigate deduplication keys; if duplicates are valid, consider aggregating rather than dropping."
    if 'outliers' in category:
        return f"Inspect outliers{col_part}: verify if they are sensor errors or true extremes. Consider winsorizing, clipping, or robust scaling depending on context."
    if 'data types' in category or 'type' in category:
        return f"Cast column types appropriately{col_part} (e.g., convert numeric-like strings to numeric or parse datetimes). Validate parsing on a sample before applying globally."
    if 'class imbalance' in category:
        return "For imbalanced categorical targets, consider resampling (oversample minority or undersample majority), use stratified sampling, or choose metrics robust to imbalance."
    if 'high correlation' in category:
        return f"Remove or combine highly correlated features{col_part} (e.g., PCA, drop one column, or create aggregated features) to avoid multicollinearity."
    if 'constant column' in category or 'constant' in category:
        return f"Drop constant column{col_part}; it provides no predictive signal."

    # Default generic suggestion
    return "Inspect the issue and apply standard preprocessing: validation, cleaning, type conversions, imputation, and resampling as appropriate."

async def init_app(q: Q):
    q.page['meta'] = ui.meta_card(
        box='',
        title='AI Dataset Quality Analyzer',
        layouts=[
            ui.layout(
                breakpoint='xs',
                zones=[
                    ui.zone('header'),
                    ui.zone('content', direction=ui.ZoneDirection.ROW, zones=[
                        ui.zone('left', size='65%'),
                        ui.zone('right', size='35%')
                    ]),
                    ui.zone('footer')
                ]
            )
        ]
    )
    
    q.page['header'] = ui.header_card(
        box='header',
        title='AI Dataset Quality Analyzer',
        subtitle='Intelligent data profiling',
        icon='DataManagementSettings',
        icon_color='#00D4AA'
    )
    
    q.client.analyzing = False
    q.client.df = None
    q.client.analysis_results = None

async def show_upload_form(q: Q):
    q.page['upload'] = ui.form_card(
        box='left',
        items=[
            ui.text_xl('Upload Your Dataset'),
            ui.text('Supported formats: CSV, Excel (XLSX, XLS)'),
            ui.file_upload(
                name='dataset_file',
                label='Choose file',
                multiple=False,
                file_extensions=['csv', 'xlsx', 'xls'],
                max_file_size=50,
                max_size=50
            ),
            ui.buttons([
                ui.button(name='analyze_dataset', label='Analyze Dataset', primary=True, disabled=True)
            ])
        ]
    )
    
    q.page['info'] = ui.form_card(
        box='right',
        items=[
            ui.text_xl('What This Tool Does'),
            ui.text('**Intelligent Analysis**: AI-powered detection of data quality issues'),
            ui.text('**Visual Insights**: Interactive charts and distributions'),
            ui.text('**Smart Recommendations**: Contextual fix suggestions'),
            ui.text('**Detailed Reports**: Executive summaries and technical findings'),
            ui.separator(),
            ui.text_s('**Detected Issues:**'),
            ui.text_xs('• Missing values & patterns'),
            ui.text_xs('• Outliers & anomalies'),
            ui.text_xs('• Data type mismatches'),
            ui.text_xs('• Class imbalance'),
            ui.text_xs('• High correlations'),
            ui.text_xs('• Constant columns'),
        ]
    )

@app('/analyzer')
async def serve(q: Q):
    if not getattr(q.client, 'initialized', False):
        await init_app(q)
        await show_upload_form(q)
        q.client.initialized = True
    
    if q.args.dataset_file:
        await handle_file_upload(q)
    
    elif q.args.analyze_dataset:
        await analyze_dataset(q)
    
    elif q.args.back_to_results:
        await show_analysis_results(q)
    
    else:
        for arg_name in dir(q.args):
            if arg_name.startswith('view_issue_'):
                if getattr(q.args, arg_name):
                    idx = int(arg_name.replace('view_issue_', ''))
                    q.client.selected_issue_idx = idx
                    await show_issue_details(q)
                    break
    
    await q.page.save()

async def handle_file_upload(q: Q):
    upload_path = await q.site.download(q.args.dataset_file[0], UPLOAD_DIR)
    
    df, error = load_dataset(upload_path)
    
    if error:
        q.page['upload'].items.append(ui.message_bar(type='error', text=error))
        await q.page.save()
        return
    
    q.client.df = df
    q.client.upload_path = upload_path
    
    dataset_info = get_dataset_info(df)
    
    q.page['upload'].items = [
        ui.text_xl('Dataset Loaded Successfully'),
        ui.message_bar(type='success', text=f"Loaded {dataset_info['rows']:,} rows × {dataset_info['columns']} columns"),
        ui.text_l('**Dataset Overview**'),
        ui.text(f"📊 **Rows:** {dataset_info['rows']:,}"),
        ui.text(f"📋 **Columns:** {dataset_info['columns']}"),
        ui.text(f"💾 **Memory:** {dataset_info['memory_usage']:.2f} MB"),
        ui.text(f"❌ **Missing Values:** {dataset_info['missing_total']:,}"),
        ui.text(f"🔄 **Duplicate Rows:** {dataset_info['duplicate_rows']:,}"),
        ui.separator(),
        ui.buttons([
            ui.button(name='analyze_dataset', label='Start AI Analysis', primary=True, icon='ProcessMetaTask')
        ])
    ]
    
    await q.page.save()
    
    column_stats = get_column_stats(df)
    columns, rows = create_column_quality_table(column_stats)
    
    q.page['column_preview'] = ui.form_card(
        box='right',
        items=[
            ui.text_xl('Column Summary'),
            ui.table(
                name='column_table',
                columns=columns,
                rows=rows,
                height='500px'
            )
        ]
    )
    
    # Also show a correlation heatmap for numeric columns if available
    try:
        corr_plot = create_correlation_heatmap(df)
        if corr_plot:
            corr_plot.box = ui.box('right', height='400px')
            q.page['correlation_heatmap'] = corr_plot
    except Exception:
        # non-fatal: skip heatmap on any plotting error
        pass

    await q.page.save()


async def analyze_dataset(q: Q):
    if q.client.df is None:
        return
    
    q.page['upload'] = ui.form_card(
        box='left',
        items=[
            ui.text_xl('Analyzing Dataset...'),
            ui.progress(label='Running quality checks...', caption='Please wait')
        ]
    )
    
    try:
        del q.page['column_preview']
    except Exception:
        pass
    
    await q.page.save()
    
    df = q.client.df
    
    analyzer = DataAnalyzer(df)
    analysis = analyzer.analyze()
    
    q.page['upload'].items = [
        ui.text_xl('Generating AI Insights...'),
        ui.progress(label='Analyzing patterns...', caption='This may take 10-30 seconds')
    ]
    await q.page.save()
    
    ai_engine = AIEngine()
    
    dataset_info = get_dataset_info(df)
    
    try:
        insights = ai_engine.generate_insights(df, analysis['issues'][:5])
    except Exception as e:
        insights = f"AI insights unavailable: {e}"

    try:
        executive_summary = ai_engine.generate_executive_summary(
            analysis['quality_score'], 
            analysis['issues'],
            dataset_info
        )
    except Exception as e:
        executive_summary = f"Executive summary unavailable: {e}"
    
    q.client.analysis_results = {
        'quality_score': analysis['quality_score'],
        'issues': analysis['issues'],
        'insights': insights,
        'executive_summary': executive_summary,
        'dataset_info': dataset_info
    }
    
    await show_analysis_results(q)

async def show_analysis_results(q: Q):
    results = q.client.analysis_results
    
    try:
        del q.page['upload']
    except Exception:
        pass
    try:
        del q.page['column_preview']
    except Exception:
        pass
    try:
        del q.page['issue_detail']
    except Exception:
        pass
    try:
        del q.page['fix_suggestions']
    except Exception:
        pass
    try:
        del q.page['column_viz']
    except Exception:
        pass
    
    q.page['quality_score'] = create_quality_gauge(results['quality_score'])
    q.page['quality_score'].box = ui.box('left', height='200px')
    
    critical_count = sum(1 for i in results['issues'] if i['severity'] == 'critical')
    warning_count = sum(1 for i in results['issues'] if i['severity'] == 'warning')
    info_count = sum(1 for i in results['issues'] if i['severity'] == 'info')
    
    q.page['stats'] = ui.form_card(
        box=ui.box('left', height='200px'),
        items=[
            ui.stats([
                ui.stat(label='Total Issues', value=str(len(results['issues'])), icon='Warning'),
                ui.stat(label='Critical', value=str(critical_count), icon='StatusErrorFull', icon_color='#e74c3c'),
                ui.stat(label='Warnings', value=str(warning_count), icon='Info', icon_color='#f39c12'),
                ui.stat(label='Info', value=str(info_count), icon='InfoSolid', icon_color='#3498db'),
            ])
        ]
    )
    
    q.page['severity_chart'] = create_issue_severity_chart(results['issues'])
    q.page['severity_chart'].box = ui.box('right', height='400px')
    
    q.page['summary'] = ui.form_card(
        box='left',
        items=[
            ui.text_xl('Executive Summary'),
            ui.text(results['executive_summary']),
            ui.separator(),
            ui.text_l('AI Insights'),
            ui.text(results['insights']),
        ]
    )
    
    issue_items = [ui.text_xl('Detected Issues')]
    
    for idx, issue in enumerate(results['issues'][:10]):
        issue_items.append(
            ui.message_bar(
                type='error' if issue['severity'] == 'critical' else 'warning' if issue['severity'] == 'warning' else 'info',
                text=f"**{issue['title']}** - {issue['description']}"
            )
        )
        
        # Inline quick-fix summary (fast, rule-based) shown immediately
        issue_items.append(ui.text_l('Suggested Fix'))
        issue_items.append(ui.text_s(_generate_quick_fix(issue)))

        # Placeholder for AI-generated suggestion (will be filled below)
        issue_items.append(ui.text_l('AI Suggested Fix'))
        issue_items.append(ui.text_s('Generating AI suggestion...'))
    
    if len(results['issues']) > 10:
        issue_items.append(ui.text_s(f"*Showing 10 of {len(results['issues'])} issues*"))
    
    q.page['issues_list'] = ui.form_card(
        box='right',
        items=issue_items
    )
    
    await q.page.save()

    # Generate AI-powered suggestions for the top N issues and update the card as they complete.
    ai_engine = AIEngine()
    max_ai = min(5, len(results['issues']))
    for ai_idx in range(max_ai):
        issue = results['issues'][ai_idx]
        try:
            ai_text = await asyncio.wait_for(
                asyncio.to_thread(ai_engine.suggest_fixes, issue, q.client.df.head(20)),
                timeout=25.0
            )
        except asyncio.TimeoutError:
            ai_text = 'AI suggestion timed out.'
        except Exception as e:
            ai_text = f'AI error: {e}'

        # store into results so future views can see it
        results['issues'][ai_idx]['ai_suggestion'] = ai_text

        # Rebuild the issues list items to include the newly obtained AI suggestion
        new_items = [ui.text_xl('Detected Issues')]
        for idx, issue in enumerate(results['issues'][:10]):
            new_items.append(
                ui.message_bar(
                    type='error' if issue['severity'] == 'critical' else 'warning' if issue['severity'] == 'warning' else 'info',
                    text=f"**{issue['title']}** - {issue['description']}"
                )
            )

            new_items.append(ui.text_l('Suggested Fix'))
            new_items.append(ui.text_s(_generate_quick_fix(issue)))

            new_items.append(ui.text_l('AI Suggested Fix'))
            ai_out = issue.get('ai_suggestion') if issue.get('ai_suggestion') else 'Generating AI suggestion...'
            new_items.append(ui.text_s(ai_out))

        if len(results['issues']) > 10:
            new_items.append(ui.text_s(f"*Showing 10 of {len(results['issues'])} issues*"))

        q.page['issues_list'].items = new_items
        await q.page.save()


async def show_issue_details(q: Q):
    issue_idx = q.client.selected_issue_idx
    results = q.client.analysis_results
    issue = results['issues'][issue_idx]
    
    try:
        del q.page['quality_score']
        del q.page['stats']
        del q.page['summary']
        del q.page['issues_list']
        del q.page['severity_chart']
    except Exception:
        pass
    
    q.page['issue_detail'] = ui.form_card(
        box='left',
        items=[
            ui.buttons([
                ui.button(name='back_to_results', label='← Back to Results')
            ]),
            ui.separator(),
            ui.text_xl(f'Issue Details: {issue["title"]}'),
            ui.message_bar(
                type='error' if issue['severity'] == 'critical' else 'warning' if issue['severity'] == 'warning' else 'info',
                text=f"**Severity:** {issue['severity'].upper()}"
            ),
            ui.text_l('Description'),
            ui.text(issue['description']),
            ui.separator(),
            ui.text_l('Category'),
            ui.text(issue['category']),
        ]
    )
    
    if issue['columns']:
        q.page['issue_detail'].items.extend([
            ui.separator(),
            ui.text_l('Affected Columns'),
            ui.text(', '.join(issue['columns']))
        ])
    
    q.page['fix_suggestions'] = ui.form_card(
        box='right',
        items=[
            ui.text_xl('AI-Generated Fix Suggestions'),
            ui.progress(label='Generating recommendations...', caption='Analyzing the issue')
        ]
    )
    
    await q.page.save()
    
    df = q.client.df

    def _init_and_suggest(issue_obj, df_sample):
        engine = AIEngine()
        return engine.suggest_fixes(issue_obj, df_sample)

    try:
        fix_suggestion = await asyncio.wait_for(
            asyncio.to_thread(_init_and_suggest, issue, df.head(20)),
            timeout=25.0
        )
    except asyncio.TimeoutError:
        fix_suggestion = "AI suggestion timed out after 25s. Try again or check your API key."
    except Exception as e:
        fix_suggestion = f"Error generating fix suggestions: {e}"

    q.page['fix_suggestions'].items = [
        ui.text_xl('AI-Generated Fix Suggestions'),
        ui.text(fix_suggestion),
        ui.separator(),
        ui.text_l('Quick Actions'),
        ui.text_s('*Manual fixes required - download your data and apply transformations*'),
    ]
    
    if issue['columns'] and len(issue['columns']) > 0:
        col_name = issue['columns'][0]
        if col_name in df.columns:
            try:
                plot = create_distribution_plot(df, col_name)
                if plot:
                    plot.box = 'right'
                    q.page['column_viz'] = plot
            except:
                pass
    
    await q.page.save()


@app('/')
async def root(q: Q):
    await serve(q)