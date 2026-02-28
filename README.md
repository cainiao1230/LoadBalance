# FastAPI负载均衡 技术实现
# 背景意义
目前低空经济发展迅猛，尤其是无人机行业，随着大量无人机的涌现，新的法令法规已经开发逐步实施，对无人机的侦测，打压等技术在慢慢走向成熟，该项目主要解决的业务是反无人机，通过改平台能够获取无人机的经纬度，高度等信息
# 启动命令
uvicorn main:app --host 0.0.0.0 --port 5000
该项目已部署在阿里云
# 解决问题:
用户将收到的大疆无人机数据包发送到解密服务器，一旦客户量增大，需要增加服务器，从而需要进行服务器负载均衡
该项目是用fastapi实现的，redis作为消息队列，请求在消息队列中更具设定的优先级规则进行排队，woker每次都会从队列中拿出优先级最高的请求从而发送到目的服务器。

# 相关接口
- 登录接口
```
POST https://192.0.2.1/api/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```
- 解密接口
```
GET https://192.0.2.1/api/yd/decryptl?hex={HEX_DATA}&token={TOKEN}
```
- 状态查询接口
```
GET https://192.0.2.1/api/yd/status?token={TOKEN}
```
- 错误日志接口
```
GET https://192.0.2.1/api/yd/errorlog?token={TOKEN}
```
- 配置接口
```
GET https://192.0.2.1/api/yd/config?token={TOKEN}
```
