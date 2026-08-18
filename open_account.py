# -*- coding: utf-8 -*-
"""
open_account.py - 打开账号池中已登录的账号

围绕 test.py 验证过的启动方式（仅设置调试端口 + 用户数据目录），
从账号数据目录恢复登录态和已安装插件。

用法：
    python open_account.py                # 展示账号池并选择
    python open_account.py 账号名          # 直接打开指定账号
"""

import json
import sys
from pathlib import Path

from DrissionPage import ChromiumPage, ChromiumOptions

BASE_DIR = Path(__file__).resolve().parent
PROFILES_DIR = BASE_DIR / 'profiles'
ACCOUNTS_FILE = BASE_DIR / 'accounts.json'
CONFIG_FILE = BASE_DIR / 'config.json'

PAGES = {}


def load_json(path):
    if path.exists():
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {}


def build_options(acc):
    co = ChromiumOptions()
    co.set_local_port(acc['port'])
    co.set_user_data_path(PROFILES_DIR / acc['profile_dir'])
    return co


def open_account(acc, cfg):
    name = acc['name']
    if name in PAGES:
        try:
            PAGES[name].to_front()
            if cfg.get('dola_url'):
                PAGES[name].get(cfg['dola_url'])
            print(f'[{name}] 已在运行，已置前')
            return
        except Exception:
            PAGES.pop(name, None)
    print(f'[{name}] 正在打开浏览器（恢复登录态与插件）...')
    page = ChromiumPage(build_options(acc))
    PAGES[name] = page
    if cfg.get('dola_url'):
        page.get(cfg['dola_url'])


def show_pool(accounts):
    print()
    print('账号池:')
    for i, a in enumerate(accounts, 1):
        status = '已登录' if a.get('logged_in') else '未登录'
        running = '·运行中' if a['name'] in PAGES else ''
        print(f"  {i}. {a['name']}  [{status}{running}]")


def main():
    cfg = load_json(CONFIG_FILE)
    accounts = load_json(ACCOUNTS_FILE)
    if not isinstance(accounts, list) or not accounts:
        print('账号池为空，请先用 dola_accounts.py 添加账号')
        return

    print('=' * 46)
    print('   打开已登录账号 (DrissionPage)')
    print('=' * 46)

    if len(sys.argv) > 1:
        targets = [a for a in accounts if a['name'] == sys.argv[1]]
        if not targets:
            print(f'账号池中未找到: {sys.argv[1]}')
            return
        try:
            open_account(targets[0], cfg)
        except Exception as e:
            print(f'打开失败: {e}')
        return

    while True:
        show_pool(accounts)
        print()
        print('输入序号打开对应账号 | 0 退出（浏览器保持开启）')
        sel = input('> ').strip()
        if sel.isdigit():
            idx = int(sel)
            if idx == 0:
                print('已退出。浏览器保持开启，登录态与插件均已持久化。')
                return
            if 1 <= idx <= len(accounts):
                try:
                    open_account(accounts[idx - 1], cfg)
                except Exception as e:
                    print(f'打开失败: {e}')
            else:
                print('序号无效')
        else:
            print('无效输入')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(0)