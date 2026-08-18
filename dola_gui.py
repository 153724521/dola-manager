# -*- coding: utf-8 -*-
"""
dola_gui.py - Dola 多账号管理器 (统一 GUI)

功能：
    - 展示账号池（登录状态 / 运行状态）
    - 打开已登录账号（恢复登录态与插件）
    - 添加新账号（手动登录流程）
    - 删除账号

用法：
    python dola_gui.py
"""

import json
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

import dola_accounts as m

BASE_DIR = Path(__file__).resolve().parent


class DolaApp:
    def __init__(self, root):
        self.root = root
        self.cfg = m.load_config()
        self.accounts = m.load_accounts()

        root.title('Dola 多账号管理器')
        root.geometry('620x420')
        root.minsize(520, 320)

        toolbar = ttk.Frame(root)
        toolbar.pack(fill='x', padx=8, pady=6)
        ttk.Button(toolbar, text='打开账号', command=self.open_selected).pack(side='left', padx=4)
        ttk.Button(toolbar, text='添加账号', command=self.add_account).pack(side='left', padx=4)
        ttk.Button(toolbar, text='删除账号', command=self.delete_account).pack(side='left', padx=4)
        ttk.Button(toolbar, text='刷新', command=self.refresh).pack(side='left', padx=4)
        ttk.Button(toolbar, text='退出', command=root.destroy).pack(side='right', padx=4)

        cols = ('name', 'status', 'running', 'port')
        self.tree = ttk.Treeview(root, columns=cols, show='headings', selectmode='browse')
        self.tree.heading('name', text='账号')
        self.tree.heading('status', text='登录状态')
        self.tree.heading('running', text='运行状态')
        self.tree.heading('port', text='端口')
        self.tree.column('name', width=180, anchor='w')
        self.tree.column('status', width=90, anchor='center')
        self.tree.column('running', width=90, anchor='center')
        self.tree.column('port', width=60, anchor='center')
        self.tree.pack(fill='both', expand=True, padx=8, pady=(0, 4))
        self.tree.bind('<Double-1>', lambda e: self.open_selected())

        self.status = ttk.Label(root, anchor='w', foreground='#555')
        self.status.pack(fill='x', padx=8, pady=(0, 6))

        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i, a in enumerate(self.accounts, 1):
            status = '已登录' if a.get('logged_in') else '未登录'
            running = '运行中' if a['name'] in m.PAGES else '未打开'
            self.tree.insert('', 'end', iid=str(i - 1),
                             values=(a['name'], status, running, a['port']))
        n = len(self.accounts)
        open_n = sum(1 for a in self.accounts if a['name'] in m.PAGES)
        self.status.config(text=f'账号池: {n} 个账号 | 运行中: {open_n} | 浏览器关闭不影响登录态')

    def selected_account(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('提示', '请先选择一个账号')
            return None
        return self.accounts[int(sel[0])]

    def open_selected(self):
        acc = self.selected_account()
        if not acc:
            return
        try:
            self.open_account(acc)
        except Exception as e:
            messagebox.showerror('打开失败', str(e))
        self.refresh()

    def open_account(self, acc):
        name = acc['name']
        if name in m.PAGES:
            try:
                m.PAGES[name].to_front()
                if self.cfg.get('dola_url'):
                    m.PAGES[name].get(self.cfg['dola_url'])
                self.status.config(text=f'[{name}] 已在运行，已置前')
                return
            except Exception:
                m.PAGES.pop(name, None)
        page = m.ChromiumPage(m.build_options(acc['profile_dir'], acc['port'], self.cfg))
        m.PAGES[name] = page
        if self.cfg.get('dola_url'):
            page.get(self.cfg['dola_url'])
        self.status.config(text=f'[{name}] 已打开（登录态与插件已恢复）')

    def add_account(self):
        name = simpledialog.askstring('添加账号', '账号备注名（如 小号1）:', parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            messagebox.showwarning('提示', '备注名不能为空')
            return
        if any(a['name'] == name for a in self.accounts):
            messagebox.showwarning('提示', f'账号 [{name}] 已存在')
            return
        profile_dir = m.sanitize_name(name)
        while any(a['profile_dir'] == profile_dir for a in self.accounts):
            profile_dir += '_'
        port = m.pick_port(self.accounts)
        (m.PROFILES_DIR / profile_dir).mkdir(parents=True, exist_ok=True)
        try:
            page = m.ChromiumPage(m.build_options(profile_dir, port, self.cfg))
        except Exception as e:
            messagebox.showerror('启动失败', str(e))
            shutil.rmtree(m.PROFILES_DIR / profile_dir, ignore_errors=True)
            return
        m.PAGES[name] = page
        if self.cfg.get('dola_url'):
            page.get(self.cfg['dola_url'])
        messagebox.showinfo(
            '手动登录',
            f'请在浏览器窗口中手动完成 Google SSO 与 Dola 登录，\n'
            f'完成后点击"确定"，账号将加入账号池。',
            parent=self.root)
        self.accounts.append({
            'name': name,
            'profile_dir': profile_dir,
            'port': port,
            'logged_in': True,
        })
        m.save_accounts(self.accounts)
        self.refresh()
        self.status.config(text=f'[{name}] 已加入账号池，登录态已持久化')

    def delete_account(self):
        acc = self.selected_account()
        if not acc:
            return
        if not messagebox.askyesno('确认删除', f'确认删除账号 [{acc["name"]}]？', parent=self.root):
            return
        page = m.PAGES.pop(acc['name'], None)
        if page is not None:
            try:
                page.quit()
            except Exception:
                pass
        if messagebox.askyesno('删除数据', '是否同时删除该账号的浏览器数据（登录态将失效）？', parent=self.root):
            shutil.rmtree(m.PROFILES_DIR / acc['profile_dir'], ignore_errors=True)
        self.accounts = [a for a in self.accounts if a['name'] != acc['name']]
        m.save_accounts(self.accounts)
        self.refresh()
        self.status.config(text=f'账号 [{acc["name"]}] 已删除')


def main():
    root = tk.Tk()
    DolaApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()