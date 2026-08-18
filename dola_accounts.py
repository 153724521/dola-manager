# -*- coding: utf-8 -*-
"""
Dola 多账号登录态管理器 (DrissionPage)

每个账号使用独立的 user_data_path + 独立调试端口，
相当于 Playwright 的独立 BrowserContext（隔离 cookie / localStorage / session），
登录态持久化保存在本地 profiles/ 目录，重启电脑后依然有效。

登录流程完全由用户在浏览器窗口中手动完成（Google SSO + Dola），
本脚本只负责：维护账号池、开窗、保持运行、复用各账号的持久化登录态。

用法：
    python dola_accounts.py
"""

import json
import re
import shutil
import socket
import sys
from pathlib import Path

from DrissionPage import ChromiumPage, ChromiumOptions

BASE_DIR = Path(__file__).resolve().parent
PROFILES_DIR = BASE_DIR / 'profiles'
ACCOUNTS_FILE = BASE_DIR / 'accounts.json'
CONFIG_FILE = BASE_DIR / 'config.json'

DEFAULT_CONFIG = {
    'dola_url': 'https://dola.me',
    'browser_path': '',
    'extension_path': '',
}

PAGES = {}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding='utf-8') as f:
            cfg.update(json.load(f))
    else:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


def load_accounts():
    if ACCOUNTS_FILE.exists():
        with open(ACCOUNTS_FILE, encoding='utf-8') as f:
            return json.load(f)
    return []


def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def pick_port(accounts):
    used = {a['port'] for a in accounts}
    port = 9223
    while port in used or not is_port_free(port):
        port += 1
    return port


def build_options(profile_dir, port, cfg):
    co = ChromiumOptions()
    co.set_user_data_path(PROFILES_DIR / profile_dir)
    co.set_local_port(port)
    co.set_argument('--start-maximized')
    co.set_argument('--no-first-run')
    co.set_argument('--no-default-browser-check')
    if cfg.get('browser_path'):
        co.set_browser_path(cfg['browser_path'])
    if cfg.get('extension_path'):
        ext = Path(cfg['extension_path'])
        if ext.exists() and (ext / 'manifest.json').exists():
            co.add_extension(str(ext))
        else:
            print(f'警告: 插件路径无效，跳过加载: {ext}')
    return co


def open_account(acc, cfg, goto_dola=True):
    if acc['name'] in PAGES:
        try:
            PAGES[acc['name']].to_front()
            print(f"[{acc['name']}] 浏览器已在运行，已置前")
            return PAGES[acc['name']]
        except Exception:
            PAGES.pop(acc['name'], None)
    print(f"[{acc['name']}] 正在打开浏览器（自动恢复登录态）...")
    page = ChromiumPage(build_options(acc['profile_dir'], acc['port'], cfg))
    PAGES[acc['name']] = page
    if goto_dola and cfg.get('dola_url'):
        page.get(cfg['dola_url'])
    return page


def close_account(acc):
    page = PAGES.pop(acc['name'], None)
    if page is not None:
        try:
            page.quit()
            print(f"[{acc['name']}] 浏览器已关闭")
        except Exception:
            pass


def sanitize_name(name):
    name = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    return name or 'account'


def show_pool(accounts):
    print()
    print('账号池:')
    if not accounts:
        print('  （空，按 N 添加第一个账号）')
        return
    for i, a in enumerate(accounts, 1):
        status = '已登录' if a.get('logged_in') else '未登录'
        running = '·运行中' if a['name'] in PAGES else ''
        print(f"  {i}. {a['name']}  [{status}{running}]")


def add_account(accounts, cfg):
    name = input('账号备注名（如 小号1）: ').strip()
    if not name:
        print('备注名不能为空')
        return accounts
    if any(a['name'] == name for a in accounts):
        print(f'账号 [{name}] 已存在')
        return accounts
    profile_dir = sanitize_name(name)
    while any(a['profile_dir'] == profile_dir for a in accounts):
        profile_dir += '_'
    port = pick_port(accounts)
    (PROFILES_DIR / profile_dir).mkdir(parents=True, exist_ok=True)

    page = ChromiumPage(build_options(profile_dir, port, cfg))
    PAGES[name] = page
    if cfg.get('dola_url'):
        page.get(cfg['dola_url'])

    print()
    print('请在弹出的浏览器窗口中手动完成 Google SSO 与 Dola 登录')
    if cfg.get('dola_url'):
        print(f'（已自动打开 {cfg["dola_url"]}）')
    print('登录完成后，回到本终端')
    input('按回车确认登录完成...')

    accounts.append({
        'name': name,
        'profile_dir': profile_dir,
        'port': port,
        'logged_in': True,
    })
    save_accounts(accounts)
    print(f'账号 [{name}] 已加入账号池，登录态已持久化到本地')
    return accounts


def main():
    cfg = load_config()
    accounts = load_accounts()

    print('=' * 46)
    print('   Dola 多账号登录态管理器 (DrissionPage)')
    print('=' * 46)

    while True:
        show_pool(accounts)
        print()
        print('输入序号打开对应账号 | N 新增账号 | D 删除账号 | 0 退出（浏览器保持开启）')
        sel = input('> ').strip().lower()

        if sel.isdigit():
            idx = int(sel)
            if idx == 0:
                print()
                print('已退出。浏览器窗口保持开启，账号池登录态已持久化到本地。')
                print('下次运行本脚本，输入序号即可直接打开对应已登录账号。')
                return
            if 1 <= idx <= len(accounts):
                try:
                    open_account(accounts[idx - 1], cfg)
                except Exception as e:
                    print(f'打开失败: {e}')
            else:
                print('序号无效')

        elif sel in ('n', 'new', 'add'):
            try:
                accounts = add_account(accounts, cfg)
            except Exception as e:
                print(f'添加失败: {e}')

        elif sel in ('d', 'del', 'delete'):
            if not accounts:
                print('账号池为空')
                continue
            show_pool(accounts)
            num = input('输入要删除的账号序号（回车取消）: ').strip()
            if not num:
                continue
            if not (num.isdigit() and 1 <= int(num) <= len(accounts)):
                print('序号无效')
                continue
            acc = accounts[int(num) - 1]
            confirm = input(f'确认删除 [{acc["name"]}]？(y/N): ').strip().lower()
            if confirm != 'y':
                continue
            close_account(acc)
            if input('是否同时删除该账号浏览器数据（登录态将失效）？(y/N): ').strip().lower() == 'y':
                shutil.rmtree(PROFILES_DIR / acc['profile_dir'], ignore_errors=True)
            accounts.pop(int(num) - 1)
            save_accounts(accounts)
            print(f'账号 [{acc["name"]}] 已从账号池删除')

        else:
            print('无效输入')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print('已退出。浏览器保持开启，登录态已保存。')
        sys.exit(0)