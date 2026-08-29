r"""
Test script to generate dashboard HTML files (daily and month-to-date) without sending emails
or copying files to the report server.

Usage (PowerShell):
& x:/fasapython/sistema-fasa/venv/Scripts/Activate.ps1; python .\dashboard\test_generate_reports.py

This script monkeypatches the `EmailSender` used by `SalesDashboard` to avoid sending emails
and ensures the server copy step is skipped by returning False for the configured UNC path.
"""
import os
import sys
import glob
import argparse

# ensure project root is on sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# import module and class
from dashboard.SalesDashboard import SalesDashboard
import dashboard.SalesDashboard as SDmod

# Dummy EmailSender used when --send is NOT provided
class DummyEmailSender:
    def __init__(self, smtp_config):
        self._cfg = smtp_config
    def send_email(self, html_content, fecha, filename=None, report_type='daily', **kwargs):
        print(f"[TEST] Suppressed send_email for fecha={fecha}, report_type={report_type}. HTML length={len(html_content) if html_content else 0}")
        return True
    def send_files(self, subject, body_text, files, to_emails=None):
        print(f"[TEST] Suppressed send_files subject={subject} files={files} to={to_emails}")
        return True

# Monkeypatch os.path.exists so the UNC server path is treated as not present (skip copy)
_original_exists = os.path.exists
_SERVER_PATH = r"\\192.168.0.195\web\informes"

def _fake_exists(path):
    if os.path.normcase(path) == os.path.normcase(_SERVER_PATH):
        return False
    return _original_exists(path)

os.path.exists = _fake_exists


def generate_reports(send=False, test_email=None, only_monthly=False, only_daily=False, empresa_id=None):
    generated = []

    # Prepare which runs to do
    runs = []
    if only_monthly and only_daily:
        raise ValueError("Cannot use --only-monthly and --only-daily together")
    if only_monthly:
        runs = ['monthly']
    elif only_daily:
        runs = ['daily']
    else:
        runs = ['daily', 'monthly']

    # If send==False, monkeypatch EmailSender to avoid sending
    if not send:
        SDmod.EmailSender = DummyEmailSender
        os.environ['SKIP_VENDEDOR_DETAIL_EMAIL'] = '1'

    # Optionally monkeypatch DatabaseManager to inject empresa_id when provided
    _orig_dbmgr = getattr(SDmod, 'DatabaseManager', None)
    if empresa_id is not None and _orig_dbmgr is not None:
        def _dbmgr_proxy(cfg, *args, _e=empresa_id, _orig=_orig_dbmgr, **kwargs):
            kwargs['empresa_id'] = _e
            return _orig(cfg, *args, **kwargs)

        SDmod.DatabaseManager = _dbmgr_proxy

    try:
        for r in runs:
            if r == 'daily':
                d = SalesDashboard()
                d.acumulado_mes = False
                if test_email:
                    d.smtp_config['to_emails'] = [test_email]
                print("[TEST] Generating daily report...")
                d.run()
            elif r == 'monthly':
                m = SalesDashboard()
                m.acumulado_mes = True
                if test_email:
                    m.smtp_config['to_emails'] = [test_email]
                print("[TEST] Generating month-to-date report...")
                m.run()
    finally:
        # Restore patched functions
        os.path.exists = _original_exists
        if _orig_dbmgr is not None:
            SDmod.DatabaseManager = _orig_dbmgr

    # List generated files in current directory
    cwd = os.getcwd()
    files = glob.glob(os.path.join(cwd, 'dashboard_ventas_*.html'))
    files.sort(key=os.path.getmtime)
    print('\n[TEST] Generated files:')
    for f in files:
        print(f"- {f}")
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate dashboard reports for testing.')
    parser.add_argument('--test-email', help='Email address to use as recipient for test sends')
    parser.add_argument('--send', action='store_true', help='Actually send emails (requires SMTP configured)')
    parser.add_argument('--only-monthly', action='store_true', help='Generate only the monthly acumulado report')
    parser.add_argument('--only-daily', action='store_true', help='Generate only the daily report')
    parser.add_argument('--empresa-id', type=int, help='Empresa ID to use for queries (overrides .env)')
    args = parser.parse_args()

    generate_reports(send=args.send, test_email=args.test_email, only_monthly=args.only_monthly, only_daily=args.only_daily, empresa_id=args.empresa_id)
