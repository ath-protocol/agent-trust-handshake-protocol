# Agent Trust Handshake Protocol (ATH Protocol)
<div align="center">
<img src="https://img.shields.io/badge/version-0.1-blue.svg" alt="version">
<img src="https://img.shields.io/badge/license-Apache%20-green.svg" alt="license">
<img src="https://img.shields.io/badge/status-draft-orange.svg" alt="status">
</div>
## 📖 协议概述
Agent Trust Handshake Protocol（ATH协议）是一套面向异构AI智能体的去中心化信任建立与安全通信标准，定义了智能体之间身份验证、权限协商、安全通信的完整流程规范，解决不同厂商、不同架构、不同功能的AI智能体之间可信互操作问题。
## 🎯 核心目标
1. **身份可验证**：所有参与交互的智能体身份可通过加密算法进行验证，防止身份伪造
2. **权限可协商**：交互双方可通过标准化流程协商数据访问范围和功能调用权限，实现最小权限授权
3. **通信可追溯**：所有交互行为可审计、可追溯，明确责任边界
4. **跨平台兼容**：支持不同技术栈、不同运行环境的智能体无缝对接
5. **安全可保障**：内置多层安全机制，防止数据泄露、未授权访问等安全风险
## 🔄 完整13步握手流程
ATH协议握手过程分为4个核心阶段：
### 第一阶段：身份宣告阶段（2步）
1. 客户端身份宣告：智能体A向智能体B发送握手请求，包含身份标识DID、能力清单
2. 服务端身份回应：智能体B向智能体A返回握手响应，包含自身身份标识DID、能力清单
### 第二阶段：身份验证阶段（4步）
3. 服务端验证请求：智能体B向身份注册中心发送智能体A的身份信息进行验证
4. 服务端验证结果：身份注册中心向智能体B返回智能体A的身份验证结果
5. 客户端验证请求：智能体A向身份注册中心发送智能体B的身份信息进行验证
6. 客户端验证结果：身份注册中心向智能体A返回智能体B的身份验证结果
### 第三阶段：权限协商阶段（4步）
7. 权限请求：智能体A向智能体B发送权限请求清单，包含请求访问的接口、数据范围
8. 权限质询：智能体B向智能体A返回权限质询，要求提供对应的验证材料
9. 权限审批：智能体A提交验证材料后，智能体B返回权限审批结果（同意/拒绝/部分同意）
10. 权限确认：智能体A向智能体B确认最终的权限范围
### 第四阶段：会话建立阶段（3步）
11. 密钥协商请求：智能体A向智能体B发送会话密钥协商请求
12. 密钥协商响应：智能体B向智能体A返回会话密钥协商响应
13. 握手完成：双方建立加密通信会话，开始业务交互
## ✨ 核心特性
- **去中心化身份**：采用DID（去中心化身份标识）作为唯一身份，无单点故障
- **双向身份验证**：双方独立验证对方身份真实性，防止中间人攻击
- **细粒度权限控制**：支持接口级、数据级、时间级的授权，遵循最小权限原则
- **端到端加密通信**：基于TLS 1.3的加密传输，支持前向保密
- **可审计性**：所有过程都有记录，满足审计和合规要求
## 📚 文档目录
### 协议规范
- [基础握手流程规范](specification/0.1/basic/handshake-flow.md)
- [客户端握手流程](specification/0.1/client/handshake-flow.md)
- [服务端握手流程](specification/0.1/server/handshake-flow.md)
- [客户端参考实现](specification/0.1/client/reference-implementation.md)
- [服务端参考实现](specification/0.1/server/reference-implementation.md)
- [中文注释版协议](specification/ath-protocol-chinese-commented.md)
### 示例代码
- [购物场景示例](example/shopping-scenario.mdx)
- [网关场景示例](example/gateway-scenario.mdx)
### 中文文档
- [可信握手协议介绍](zh/docs/learn/trusted-handshake.mdx)
- [中文基础流程规范](specification/0.1/basic/handshake-flow.zh.mdx)
- [场景示例](zh/docs/examples/scenario.mdx)
## 🏗️ 协议架构
ATH协议采用分层架构设计：
1. **身份层**：负责身份的生成、验证和管理
2. **权限层**：负责权限的协商、审批和控制
3. **会话层**：负责加密会话的建立和管理
4. **应用层**：负责业务数据的传输和处理
## 🔒 安全机制
### 身份安全
- 去中心化DID身份体系，不依赖单一权威机构
- 所有身份信息都通过数字签名防止篡改
### 权限安全
- 细粒度权限控制，支持多维权限限制
- 权限到期自动失效，支持主动吊销
### 通信安全
- TLS 1.3加密协议，支持前向保密
- 端到端加密，防止数据泄露
### 审计安全
- 完整的审计日志记录
- 日志不可篡改，支持事后追溯
## 🤝 贡献
欢迎提交Issue和Pull Request来完善协议规范。
## 📄 许可证
本项目采用 Apache 2.0 许可证，详见 [LICENSE](LICENSE) 文件。
