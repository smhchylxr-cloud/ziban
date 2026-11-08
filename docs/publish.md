# 发布手册（写给第一次发开源项目的人）

这份文件回答两个问题：**这个项目归谁**、**它怎么被全世界 `pip install` 到**。
不需要任何前置知识，照做即可。

---

## 一、两个地方，两件事

| | GitHub | PyPI |
|---|---|---|
| 是什么 | 放**源代码**的地方，程序员看代码、提 issue、点 star | 放**安装包**的地方，`pip install` 从这里下载 |
| 类比 | 菜谱公开贴在墙上 | 做好的半成品放在超市货架上 |
| 谁需要 | 想读代码、想参与、想 star 的人 | 只想 `pip install` 用起来的人 |
| 我们的地址 | `github.com/<你的用户名>/ziban` | `pypi.org/project/ziban` |

**仓库归属**就是"这个 GitHub 地址的第一段是谁"。
它决定了：谁能改代码、issue 提到谁、star 算谁的、以后能不能转手。

---

## 二、归属方案（已替你定好）

**结论：先放在你的个人 GitHub 账号下，仓库名 `ziban`。**

理由，按重要性排：

1. **一个人维护，个人账号就是最合适的归属。** 组织（Organization）是给多人协作准备的，
   现在建组织只会多一层管理成本，没有任何收益。
2. **以后想搬，成本几乎为零。** GitHub 支持把仓库直接 transfer 到组织，
   **star、issue、PR、fork 全部保留，链接自动 301 跳转**。所以"先个人"不是一次性决定。
3. **包的归属和账号无关。** PyPI 上认的是包名 `ziban`（全局唯一，先到先得），
   不是你的 GitHub 用户名。以后换账号不用重发。

### 用户名怎么选

如果你**已经有 GitHub 账号**：直接用，别为了这个项目改名。

如果**没有**，注册时注意三点：

- 用**中性、可长期用**的名字（`chenh`、`ziban-dev` 这类），别用带年份或中二的昵称——
  这个名字会出现在每一个 issue、每一次 commit、PyPI 的元数据里，五年后还在。
- **邮箱用 GitHub 的 noreply 地址**（设置里勾 "Keep my email addresses private"），
  否则你的真实邮箱会被爬虫抓走，然后开始收垃圾邮件。
- 用户名一旦定了别改：改了以后旧链接会跳转，但别人嘴里的"那个 ziban 项目在 xxx 那儿"对不上。

### 填进项目里的三处

定了用户名之后，把这三处的 `<you>` 换成它（我可以代劳，你只要告诉我名字）：

1. `pyproject.toml` → `[project.urls]`
2. `README.md` 顶部的仓库链接
3. `.github/workflows/ci.yml` 的 badge（可选）

---

## 三、PyPI 发布：谁做什么

### 为什么不能全自动

PyPI 上传需要 **API token**，而 token 只能由账号持有人创建；
账号注册又要邮箱验证 + **强制两步验证（2FA）**。这两步涉及你的身份，我不能替你做。
剩下的全部我可以做。

### 你需要做的（约 10 分钟，一次性）

1. 打开 <https://pypi.org/account/register/> 注册（免费）。
2. 进 **Account settings → Two-factor authentication**，用手机上的验证器 App 开启 2FA（**必须**）。
3. 进 **Account settings → API tokens → Add API token**：
   - Token name：`ziban-upload`
   - Scope：选 **Project: ziban**（如果包还不存在，先选 "Entire account"，首次上传后改成项目级）
   - 生成后**只显示一次**，形如 `pypi-AgEIcHlwaS5vcmc...`
4. 把它放到本机环境变量里（**不要贴进聊天框、不要写进代码、不要 commit**）：

   ```powershell
   # 当前 PowerShell 会话有效
   $env:TWINE_USERNAME = "__token__"
   $env:TWINE_PASSWORD = "pypi-AgEIcHlwaS5vcmc..."   # 换成你的 token
   ```

   想长期保存（只对当前用户可见）：

   ```powershell
   [Environment]::SetEnvironmentVariable("TWINE_USERNAME", "__token__", "User")
   [Environment]::SetEnvironmentVariable("TWINE_PASSWORD", "pypi-...", "User")
   ```

### 我做的部分（已就绪）

```text
dist/ziban-0.1.0-py3-none-any.whl   23 KB
dist/ziban-0.1.0.tar.gz             85 KB
twine check  → PASSED（两个文件都通过，README 渲染无错）
干净虚拟环境安装 → 通过，`ziban wrap` 正常工作
```

上传命令（环境变量设好后，我来跑）：

```powershell
python -m twine upload dist/*
```

### 建议：先演练一次

PyPI 的版本号**发布后不能覆盖、不能删除**（只能 yank，包名永久占用）。
所以第一次建议先发到 **TestPyPI**（一个和正式库完全隔离的测试站）：

```powershell
# 在 test.pypi.org 单独注册 + 单独建 token
python -m twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ ziban
```

确认 `pip install` 干净可用之后，再发正式库。这一步能把"发错了"的概率降到零。

---

## 四、发布前检查清单

- [ ] `python -m pytest` 全绿（当前 958 passed）
- [ ] `python -m build` 生成 sdist + wheel
- [ ] `python -m twine check dist/*` 两个都 PASSED
- [ ] 干净环境 `pip install dist/*.whl` 后 `ziban wrap` 能跑
- [ ] 版本号在 `pyproject.toml` 与 `src/ziban/__init__.py` 一致（都是 `0.1.0`）
- [ ] 包名 `ziban` 在 PyPI 上仍未占用（发布前再查一次 `https://pypi.org/pypi/ziban/json`，404 即可用）

## 五、以后每次发版

1. 改 `pyproject.toml` 与 `__init__.py` 的版本号（两边必须一致）
2. 更新 `CHANGELOG.md`
3. `git tag v0.2.0 && git push --tags`
4. `python -m build && python -m twine upload dist/*`
5. GitHub 上把 tag 做成 Release，正文直接抄 CHANGELOG

**版本号规则**：`0.1.0` → 修 bug 发 `0.1.1` → 加功能发 `0.2.0` → 稳定后 `1.0.0`。
发出去的版本永远不要试图覆盖，改错了就发下一个。
