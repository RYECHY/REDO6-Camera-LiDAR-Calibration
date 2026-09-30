# 将公开包发布到 GitHub

只上传解压后的 `REDO6-Camera-LiDAR-Calibration` 目录。不要提交原审核包、完整工作空间或包含其他材料的父目录。

## 1. 创建空仓库

在 GitHub 创建仓库，建议名称 `REDO6-Camera-LiDAR-Calibration`。描述可使用：

> Final camera–LiDAR calibration parameters, projection validation, and reference tools for a cylindrical RGB camera and Livox MID-360.

远程仓库不要再次初始化 README、.gitignore 或 License；本地公开目录已包含这些文件。

## 2. 本地检查与提交

先把最终 ZIP 解压到一个新目录，避免混入旧版。可以在下载目录执行以下命令；ZIP 文件名若被浏览器加了后缀，请替换为实际文件名：

```bash
unzip "$HOME/下载/REDO6_GitHub_Final.zip" -d "$HOME/下载/redo6_publish_final"
cd "$HOME/下载/redo6_publish_final/REDO6-Camera-LiDAR-Calibration"
```

如果该输出目录已经存在，请改用另一个新的目录名，不要覆盖旧文件。以下操作从上述仓库根目录开始：

```bash
python3 scripts/check_calibration.py

git init -b main
git config user.name "你的 Git 显示名"
git config user.email "你的 GitHub noreply 邮箱或公开提交邮箱"
git add README.md LICENSE ASSET_NOTICE.md requirements.txt .gitignore config docs images results scripts launch patches third_party

git diff --cached --stat
git diff --cached --check
git diff --cached
```

确认文件清单和内容。图片已经允许纳入该公开包，原始审核材料和公司源码没有纳入。退出差异查看器可按 q。

```bash
git commit -m "Publish REDO6 calibration parameters and validation guide"
```

## 3. 推送到空仓库

先完成自己的 GitHub 命令行认证。以下命令使用已经设置好的 SSH：

```bash
git remote add origin git@github.com:你的账号/REDO6-Camera-LiDAR-Calibration.git
git remote -v
git push -u origin main
```

替换实际账号。若使用 HTTPS，请使用 GitHub 支持的认证方式，不把 token 写入代码或远程 URL。认证配置和凭据只保存在自己的本地环境。

推送完成后检查 README 图片是否显示、最终 YAML 是否可见、没有额外的工作空间或录包目录。仓库首页的复现限制也应保留。

## 官方参考

- [GitHub：把本地项目加入仓库](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)
- [GitHub：认证方式](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)
- [GitHub：添加 SSH 公钥](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)
