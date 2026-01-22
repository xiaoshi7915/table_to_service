# Nginx SSL 配置文档

## 📋 配置概述

本文档说明如何为 `wenshu.chenxiaoshivivid.top` 配置 HTTPS 访问。

## ✅ 已完成的配置

### 1. 域名配置
- **域名**: `wenshu.chenxiaoshivivid.top`
- **前端服务**: `http://127.0.0.1:3003`
- **后端API**: `http://127.0.0.1:8300`

### 2. SSL 证书
- **证书类型**: Let's Encrypt (免费SSL证书)
- **证书路径**: `/etc/letsencrypt/live/wenshu.chenxiaoshivivid.top/`
- **证书有效期**: 90天（自动续期）
- **申请日期**: 2026-01-20
- **到期日期**: 2026-04-20

### 3. Nginx 配置
- **配置文件**: `/etc/nginx/conf.d/wenshu.chenxiaoshivivid.top.conf`
- **HTTP端口**: 80（自动重定向到HTTPS）
- **HTTPS端口**: 443

## 🔧 配置详情

### Nginx 配置结构

```
HTTP (80端口)
  ├─ /.well-known/acme-challenge/  (Let's Encrypt验证路径)
  └─ /  (重定向到HTTPS)

HTTPS (443端口)
  ├─ /api/  (代理到后端服务 8300端口)
  └─ /  (代理到前端服务 3003端口)
```

### 关键配置项

1. **SSL 证书路径**:
   ```nginx
   ssl_certificate /etc/letsencrypt/live/wenshu.chenxiaoshivivid.top/fullchain.pem;
   ssl_certificate_key /etc/letsencrypt/live/wenshu.chenxiaoshivivid.top/privkey.pem;
   ```

2. **SSL 协议和加密套件**:
   ```nginx
   ssl_protocols TLSv1.2 TLSv1.3;
   ssl_ciphers PROFILE=SYSTEM;
   ```

3. **安全头设置**:
   - `Strict-Transport-Security`: 强制HTTPS
   - `X-Frame-Options`: 防止点击劫持
   - `X-Content-Type-Options`: 防止MIME类型嗅探
   - `X-XSS-Protection`: XSS保护

4. **代理超时设置**:
   - API请求: 120秒（智能问数功能可能需要较长时间）
   - 前端请求: 60秒

## 🔄 SSL 证书自动续期

Let's Encrypt 证书有效期为90天，certbot 已设置自动续期任务。

### 检查自动续期任务

```bash
# 查看certbot定时任务
systemctl list-timers | grep certbot

# 或查看cron任务
cat /etc/cron.d/certbot
```

### 手动续期测试

```bash
# 测试续期（不会真正续期）
certbot renew --dry-run

# 手动续期（如果自动续期失败）
certbot renew
```

### 续期后重载Nginx

certbot 会自动重载 nginx，但也可以手动重载：

```bash
systemctl reload nginx
```

## 🧪 测试配置

### 1. 测试 HTTP 重定向

```bash
curl -I http://wenshu.chenxiaoshivivid.top
```

应该返回 `301 Moved Permanently` 并重定向到 HTTPS。

### 2. 测试 HTTPS 连接

```bash
curl -I https://wenshu.chenxiaoshivivid.top
```

应该返回 `200 OK`。

### 3. 测试 SSL 证书

```bash
# 使用 openssl 测试
openssl s_client -connect wenshu.chenxiaoshivivid.top:443 -servername wenshu.chenxiaoshivivid.top

# 或使用在线工具
# https://www.ssllabs.com/ssltest/analyze.html?d=wenshu.chenxiaoshivivid.top
```

### 4. 测试前端访问

在浏览器中访问：
- `https://wenshu.chenxiaoshivivid.top`

### 5. 测试 API 访问

```bash
curl https://wenshu.chenxiaoshivivid.top/api/v1/health
```

## 📝 常用命令

### 查看证书信息

```bash
# 查看所有证书
certbot certificates

# 查看特定证书详情
certbot certificates -d wenshu.chenxiaoshivivid.top
```

### 检查 Nginx 配置

```bash
# 测试配置语法
nginx -t

# 查看配置
cat /etc/nginx/conf.d/wenshu.chenxiaoshivivid.top.conf
```

### 重载 Nginx

```bash
# 重载配置（不中断服务）
systemctl reload nginx

# 或重启（会短暂中断服务）
systemctl restart nginx
```

### 查看 Nginx 日志

```bash
# 访问日志
tail -f /var/log/nginx/access.log

# 错误日志
tail -f /var/log/nginx/error.log
```

## 🔍 故障排查

### 1. SSL 证书问题

**问题**: 浏览器显示"不安全"或证书错误

**排查步骤**:
1. 检查证书是否存在：
   ```bash
   ls -la /etc/letsencrypt/live/wenshu.chenxiaoshivivid.top/
   ```

2. 检查证书有效期：
   ```bash
   openssl x509 -in /etc/letsencrypt/live/wenshu.chenxiaoshivivid.top/fullchain.pem -noout -dates
   ```

3. 检查域名DNS解析：
   ```bash
   nslookup wenshu.chenxiaoshivivid.top
   ```

### 2. 502 Bad Gateway

**问题**: 访问时显示 502 错误

**排查步骤**:
1. 检查前端服务是否运行：
   ```bash
   netstat -tlnp | grep 3003
   ```

2. 检查后端服务是否运行：
   ```bash
   netstat -tlnp | grep 8300
   ```

3. 查看 Nginx 错误日志：
   ```bash
   tail -50 /var/log/nginx/error.log
   ```

### 3. 403 Forbidden

**问题**: 访问时显示 403 错误

**排查步骤**:
1. 检查文件权限：
   ```bash
   ls -la /var/www/html/.well-known/acme-challenge/
   ```

2. 检查 Nginx 配置中的 `allow all` 设置

### 4. 证书续期失败

**问题**: 自动续期失败

**排查步骤**:
1. 检查域名DNS解析是否正常
2. 检查 `/var/www/html/.well-known/acme-challenge/` 目录权限
3. 手动测试续期：
   ```bash
   certbot renew --dry-run
   ```

## 📚 相关文档

- [Let's Encrypt 官方文档](https://letsencrypt.org/docs/)
- [Certbot 官方文档](https://certbot.eff.org/)
- [Nginx SSL 配置最佳实践](https://ssl-config.mozilla.org/)

## 🔐 安全建议

1. **定期检查证书状态**: 每月检查一次证书有效期
2. **监控自动续期**: 确保自动续期任务正常运行
3. **更新SSL配置**: 关注SSL/TLS安全最佳实践，及时更新配置
4. **日志监控**: 定期查看Nginx访问日志和错误日志
5. **防火墙配置**: 确保80和443端口对外开放

## 📞 联系方式

如有问题，请联系系统管理员。

---

**最后更新**: 2026-01-20
**配置状态**: ✅ 已配置并运行正常
