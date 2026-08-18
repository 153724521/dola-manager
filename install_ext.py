# -*- coding: utf-8 -*-
"""
install_ext.py - 为账号池中的每个账号永久安装 Chrome 插件

Chrome 137+ 移除了命令行 --load-extension，因此改为模拟用户在
chrome://extensions 中手动加载已解压的扩展程序（开发者模式）。

用法：
    python install_ext.py           # 为所有账号安装
    python install_ext.py 账号名     # 只为指定账号安装
"""

import base64
import json
import subprocess
import sys
import time
from pathlib import Path

from DrissionPage import ChromiumPage, ChromiumOptions

BASE_DIR = Path(__file__).resolve().parent
PROFILES_DIR = BASE_DIR / 'profiles'
ACCOUNTS_FILE = BASE_DIR / 'accounts.json'
CONFIG_FILE = BASE_DIR / 'config.json'

MAX_EXT_NAME = '豆包 Dola 15秒去水印助手'


def load_json(path):
    if path.exists():
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {}


def build_options(profile_dir, port, cfg):
    co = ChromiumOptions()
    co.set_user_data_path(PROFILES_DIR / profile_dir)
    co.set_local_port(port)
    co.set_argument('--start-maximized')
    co.set_argument('--no-first-run')
    co.set_argument('--no-default-browser-check')
    if cfg.get('browser_path'):
        co.set_browser_path(cfg['browser_path'])
    return co


def feed_folder_dialog(ext_path):
    ps = f"""
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Clipboard]::SetText('{ext_path}')
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait('{{ENTER}}')
"""
    enc = base64.b64encode(ps.encode('utf-16-le')).decode()
    subprocess.Popen(['powershell', '-NoProfile', '-WindowStyle', 'Hidden',
                      '-EncodedCommand', enc])


def get_installed_names(root):
    try:
        items = root.ele('css:extensions-item-list', timeout=8)
        if items:
            return [e.attr('name') for e in items.eles('css:extensions-item')]
    except Exception:
        pass
    return []


def install_one(page, ext_path, ext_name):
    page.get('chrome://extensions')
    mg = page.ele('css:extensions-manager', timeout=10)
    root = mg.shadow_root
    toolbar = root.ele('css:extensions-toolbar', timeout=5)
    troot = toolbar.shadow_root

    if ext_name in get_installed_names(root):
        print(f'  插件已安装，跳过')
        return True

    dev = troot.ele('css:#devMode', timeout=5)
    if dev.attr('aria-pressed') != 'true':
        dev.click()
        time.sleep(1)

    btn = troot.ele('css:#loadUnpacked', timeout=5)
    btn.click()
    time.sleep(1.5)
    feed_folder_dialog(ext_path)

    for _ in range(10):
        time.sleep(1)
        if ext_name in get_installed_names(root):
            return True
    return False


def main():
    cfg = load_json(CONFIG_FILE)
    ext_path = cfg.get('extension_path')
    if not ext_path:
        print('config.json 中未配置 extension_path')
        return
    ext = Path(ext_path)
    if not (ext.exists() and (ext / 'manifest.json').exists()):
        print(f'插件路径无效: {ext}')
        return
    ext_name = MAX_EXT_NAME

    accounts = load_json(ACCOUNTS_FILE)
    if not isinstance(accounts, list) or not accounts:
        print('账号池为空')
        return
    targets = [a for a in accounts if a['name'] == sys.argv[1]] if len(sys.argv) > 1 else accounts
    if not targets:
        print(f'未找到账号: {sys.argv[1]}')

    for acc in targets:
        print(f'[{acc["name"]}] 安装插件...')
        try:
            page = ChromiumPage(build_options(acc['profile_dir'], acc['port'], cfg))
            ok = install_one(page, str(ext), ext_name)
            print(f'[{acc["name"]}] ' + ('插件安装成功' if ok else '安装失败，请检查浏览器中的 chrome://extensions 面板'))
            if not ok:
                input('按回车继续处理下一个账号...')
        except Exception as e:
            print(f'[{acc["name"]}] 出错: {e}')

    print()
    print('完成。插件已写入各账号的数据目录，以后每次打开浏览器都会保留。')


if __name__ == '__main__':
    main()