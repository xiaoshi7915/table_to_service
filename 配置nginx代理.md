# Nginx反向代理配置说明

## 配置说明
- 后端服务运行在 **8300** 端口
- API文档中生成的URL使用 **50052** 端口
- 需要配置nginx反向代理，将50052端口的请求转发到8300端口

## 配置步骤

### 1. 复制配置文件到nginx配置目录

```bash
# 复制配置文件
sudo cp /opt/table_to_service/nginx_proxy.conf /etc/nginx/conf.d/table_to_service_proxy.conf

# 或者创建符号链接
sudo ln -s /opt/table_to_service/nginx_proxy.conf /etc/nginx/conf.d/table_to_service_proxy.conf
```

### 2. 测试nginx配置

```bash
sudo nginx -t
```

### 3. 重载nginx配置

```bash
# 如果配置正确，重载nginx
sudo nginx -s reload

# 或者重启nginx
sudo systemctl restart nginx
```

### 4. 检查50052端口是否监听

```bash
netstat -tlnp | grep 50052
# 或
ss -tlnp | grep 50052
```

### 5. 测试代理是否工作

```bash
# 测试本地访问
curl -X GET 'http://localhost:50052/api/department'

# 测试外部访问
curl -X GET 'http://121.36.205.70:50052/api/department'
```

## 防火墙配置

确保防火墙开放50052端口：

```bash
# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=50052/tcp
sudo firewall-cmd --reload

# Ubuntu/Debian
sudo ufw allow 50052/tcp
```

## 注意事项

1. **端口冲突**：确保50052端口没有被其他服务占用
2. **权限问题**：nginx需要root权限监听1024以下的端口，50052端口不需要root权限
3. **SELinux**：如果启用了SELinux，可能需要配置相关策略

## 验证

配置完成后，访问以下URL应该能够正常返回数据：
- `http://121.36.205.70:50052/api/department`
- `http://121.36.205.70:50052/health`

