# Dola 多账号登录态管理器

基于 DrissionPage 的多账号登录态管理工具。每个账号拥有独立的浏览器数据目录（相当于 Playwright 的独立 `BrowserContext`），登录态持久化保存在本地，重启电脑后依然有效，下次直接打开已登录账号即可使用。

登录流程（Google SSO + Dola）完全由用户手动在浏览器窗口中完成，脚本只负责维护账号池、开窗、保持浏览器运行、复用持久化登录态，不做任何登录自动化，安全可靠。

## 功能

- **统一 GUI**（`dola_gui.py`）：账号池列表、打开 / 添加 / 删除账号，一键操作
- 账号池管理：新增 / 删除 / 选择账号
- 每个账号独立 `user_data_path` + 独立调试端口，cookie / localStorage / session 完全隔离
- 登录态持久化到本地 `profiles/` 目录，浏览器和脚本全部退出后依然有效
- 浏览器窗口保持开启，可同时运行多个账号
- Chrome 插件（如 Dola 去水印助手）统一安装，随账号数据目录持久化

## 依赖

- Python 3.8+
- DrissionPage：`pip install DrissionPage`

## 快速开始

```bash
python dola_gui.py        # 统一 GUI（推荐入口）
```

GUI 界面：

```
┌──────────────────────────────────────────────┐
│ [打开账号] [添加账号] [删除账号] [刷新]   [退出] │
├──────────────────────────────────────────────┤
│  账号        登录状态   运行状态     端口      │
│  google1     已登录     未打开       9223     │
│  小号1       已登录     运行中       9224     │
├──────────────────────────────────────────────┤
│ 账号池: 2 个账号 | 运行中: 1 | ...            │
└──────────────────────────────────────────────┘
```

也可以使用命令行脚本：

```bash
python dola_accounts.py          # 账号池维护（添加 / 删除账号）
python open_account.py           # 打开已登录账号（交互选择）
python open_account.py 账号名     # 直接打开指定账号
```

## 各脚本职责

| 脚本 | 职责 |
| --- | --- |
| `dola_gui.py` | 统一 GUI 入口，整合以下所有功能 |
| `dola_accounts.py` | 账号池维护：添加（手动登录）、删除账号，保存登录态 |
| `open_account.py` | 打开已登录账号：恢复登录态与插件，跳转 Dola |
| `install_ext.py` | 为账号池中所有账号安装 Chrome 插件（`python install_ext.py`，可加账号名参数指定单个账号） |

## 使用流程

1. **添加账号**：GUI 中点「添加账号」→ 输入备注名 → 浏览器自动弹出并打开 Dola → 手动完成 Google SSO 与 Dola 登录 → 弹窗点确定，账号加入账号池，登录态持久化
2. **打开账号**：选中账号点「打开账号」（或双击），浏览器用该账号的登录态启动并进入 Dola，插件同时载入
3. **删除账号**：选中点「删除账号」，可连同浏览器数据（登录态）一并删除
4. **退出**：只关闭脚本，所有浏览器窗口保持开启，登录态已保存

## 文件结构

```
dola-manager/
├── dola_gui.py          # 统一 GUI
├── dola_accounts.py     # 账号池维护（命令行）
├── open_account.py      # 打开已登录账号（命令行）
├── install_ext.py       # 插件安装脚本
├── README.md
├── config.json          # 配置（首次运行自动生成，不入库）
├── accounts.json        # 账号池（自动维护，不入库）
└── profiles/            # 各账号浏览器数据目录（登录态，不入库）
```

## 配置

`config.json`（首次运行自动生成，已加入 `.gitignore` 不入库）：

```json
{
  "dola_url": "https://dola.me",
  "browser_path": "",
  "extension_path": ""
}
```

- `dola_url`：Dola 登录页地址，如网址不同请修改
- `browser_path`：Chrome 可执行文件路径，留空则自动查找（注册表 / PATH）。使用 Chrome 系浏览器（Edge、360 等）时需填写
- `extension_path`：Chrome 插件目录（需含 `manifest.json`），供 `install_ext.py` 安装使用

## 插件安装

Chrome 137+ 已移除命令行加载插件的功能（`--load-extension` 不再生效），因此插件需"永久安装"进账号数据目录：

```bash
python install_ext.py          # 为所有账号安装
python install_ext.py 账号名    # 只为指定账号安装
```

脚本模拟手动加载流程：打开 `chrome://extensions` → 开启开发者模式 → 加载已解压的扩展程序（自动填写插件路径），完成后插件随账号数据目录持久化，每次打开账号自动载入。也可在各账号浏览器中手动执行相同操作。

## 工作原理

1. 每个账号创建时分配独立的用户数据目录（`profiles/<账号>/`）和调试端口（从 9223 起递增）
2. 浏览器以 `--user-data-dir` 指向该目录独立运行，登录产生的 cookie / localStorage 及安装的插件全部落盘持久化
3. 再次打开同一账号时：浏览器仍在运行则直接连接，已关闭则用相同目录重新启动，登录态与插件自动恢复
4. 脚本退出不影响浏览器，登录态始终保留在本地

## 常见问题

**Q: 打开账号后还是未登录状态？**
添加账号时未完成 Google SSO 全流程，或浏览器数据被删除。重新用该账号打开浏览器完成登录即可。

**Q: 提示找不到浏览器？**
未检测到 Chrome，请在 `config.json` 的 `browser_path` 填写浏览器可执行文件路径（如 Edge：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`）。

**Q: 端口被占用报错？**
删除账号时未一并删除浏览器数据、且旧浏览器仍在运行时可能出现。关闭对应账号的浏览器窗口后重试，或重启电脑。

**Q: 插件没生效？**
插件是浏览器启动时载入的，已打开的浏览器需要重新打开才会载入。若从未安装过，运行 `python install_ext.py` 或在 `chrome://extensions` 中手动加载插件目录。