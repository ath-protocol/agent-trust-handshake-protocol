#!/usr/bin/env python3
"""
ATH协议交互式演示Demo - SDK原生模式
✅ 新增特性：
1. 交互式用户授权，需要在控制台输入同意才能继续
2. 每个步骤都有炫酷的加载动画和进度提示
3. 客户端和服务端逻辑完全分离，分开展示
4. 更友好的界面效果
"""
import json
import random
import string
from typing import Dict, Any
import time
import sys
# 全局变量，控制是否显示分角色代码
show_code_separately = False
def loading_animation(text: str, duration: float = 1.5):
    """显示加载动画"""
    chars = "|/-\"
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r⏳ {text} {chars[i % len(chars)]}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(f"\r✅ {text} 完成!\n")
    sys.stdout.flush()
def print_separator(title: str = ""):
    """打印分隔线"""
    print("\n" + "="*80)
    if title:
        print(f"📌 {title}")
        print("-"*80)
def print_role_separator(role: str):
    """打印角色分隔线"""
    if role == "client":
        print("\n" + "🔵 " + "="*30 + " [客户端逻辑] " + "="*30 + " 🔵")
    elif role == "server":
        print("\n" + "🟢 " + "="*30 + " [服务端逻辑] " + "="*30 + " 🟢")
    elif role == "user":
        print("\n" + "🟣 " + "="*30 + " [用户交互] " + "="*30 + " 🟣")
# ==================== 客户端实现（完全独立） ====================
class Client:
    """客户端：AI购物助手"""
    def __init__(self):
        self.did = "did:ath:ai_shopping_assistant_001"
        self.private_key = "client_private_key_123456"
        self.public_key = "client_public_key_abcdef"
        self.user_authorization = None
        self.access_token = None
        self.server_public_key = None
        print_separator("初始化客户端")
        loading_animation("生成客户端DID身份和公私钥对")
        print(f"   客户端DID: {self.did}")
        print(f"   客户端公钥: {self.public_key[:20]}...")
        
    def get_user_authorization(self, scopes: list) -> bool:
        """获取用户预授权"""
        print_role_separator("user")
        print(f"📋 【授权请求】AI购物助手请求以下权限：")
        for scope in scopes:
            print(f"   ✅ {scope}")
        
        while True:
            choice = input("\n🤔 是否同意授权？(Y/N): ").strip().upper()
            if choice == 'Y':
                loading_animation("用户签署授权凭证")
                self.user_authorization = {
                    "user_id": "user_001",
                    "scopes": scopes,
                    "signature": "user_signature_" + ''.join(random.choices(string.hexdigits, k=16)),
                    "expires_at": int(time.time()) + 7200
                }
                print(f"   授权凭证: {self.user_authorization['signature'][:20]}...")
                return True
            elif choice == 'N':
                print("❌ 用户拒绝授权，流程终止")
                return False
            else:
                print("⚠️  请输入Y或N")
    def step1_send_handshake_request(self) -> Dict[str, Any]:
        """步骤1：发送握手请求"""
        print_role_separator("client")
        loading_animation("生成握手请求报文")
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        request = {
            "type": "handshake_request",
            "client_did": self.did,
            "client_pubkey": self.public_key,
            "nonce": nonce,
            "timestamp": int(time.time())
        }
        print(f"   随机数: {nonce}")
        print("📤 客户端 -> 服务端：发送握手请求")
        return request
    def step3_send_identity_proof(self, server_response: Dict[str, Any]) -> Dict[str, Any]:
        """步骤3：发送身份证明"""
        print_role_separator("client")
        self.server_public_key = server_response["server_pubkey"]
        server_nonce = server_response["nonce"]
        
        loading_animation("使用私钥对服务端随机数签名")
        signature = "sig_" + ''.join(random.choices(string.hexdigits, k=32))
        
        proof = {
            "type": "identity_proof",
            "signature": signature,
            "timestamp": int(time.time())
        }
        print(f"   签名: {signature[:20]}...")
        print("📤 客户端 -> 服务端：发送身份证明")
        return proof
    def step5_send_scope_request(self) -> Dict[str, Any]:
        """步骤5：发送权限请求"""
        print_role_separator("client")
        loading_animation("构建权限请求报文")
        request = {
            "type": "scope_request",
            "scopes": self.user_authorization["scopes"],
            "user_authorization": self.user_authorization,
            "context": "用户需要查询商品并下单",
            "timestamp": int(time.time())
        }
        print(f"   请求权限: {request['scopes']}")
        print("📤 客户端 -> 服务端：发送权限请求")
        return request
    def step9_complete_handshake(self, access_token: str):
        """步骤9：完成握手"""
        print_role_separator("client")
        loading_animation("验证访问令牌有效性")
        self.access_token = access_token
        print(f"   访问令牌: {access_token[:20]}...")
        print("✅ 客户端握手完成！已建立可信通信通道")
    def send_business_request(self, api_path: str, method: str = "GET", data: Dict = None):
        """发送业务请求"""
        if not self.access_token:
            print("❌ 未建立连接，请先完成握手")
            return
        
        print_separator(f"业务请求演示: {method} {api_path}")
        loading_animation(f"使用会话密钥加密请求数据")
        print(f"📤 发送请求: {method} {api_path}")
        print(f"   Authorization: Bearer {self.access_token[:20]}...")
        if data:
            print(f"   请求数据: {json.dumps(data, ensure_ascii=False)}")
        
        # 模拟响应
        loading_animation("等待服务端响应", duration=1)
        if "goods" in api_path:
            print("✅ 响应成功：返回商品列表 [{'id': '123', 'name': 'iPhone 15', 'price': 5999}]")
        elif "order" in api_path:
            print("✅ 响应成功：订单创建完成，订单号: ORDER_" + ''.join(random.choices(string.digits, k=8)))
        else:
            print("✅ 响应成功")
# ==================== 服务端实现（完全独立） ====================
class Server:
    """服务端：电商平台"""
    def __init__(self):
        self.did = "did:ath:ecommerce_platform_001"
        self.private_key = "server_private_key_654321"
        self.public_key = "server_public_key_fedcba"
        self.client_nonce = None
        self.client_did = None
        self.client_public_key = None
        print_separator("初始化服务端")
        loading_animation("加载服务端配置和证书")
        print(f"   服务端DID: {self.did}")
        print(f"   服务端公钥: {self.public_key[:20]}...")
        
    def step2_send_handshake_response(self, client_request: Dict[str, Any]) -> Dict[str, Any]:
        """步骤2：返回握手响应"""
        print_role_separator("server")
        self.client_did = client_request["client_did"]
        self.client_public_key = client_request["client_pubkey"]
        self.client_nonce = client_request["nonce"]
        
        loading_animation("验证客户端请求格式，生成服务端随机数")
        server_nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        loading_animation("使用私钥对客户端随机数签名")
        signature = "sig_" + ''.join(random.choices(string.hexdigits, k=32))
        
        response = {
            "type": "handshake_response",
            "server_did": self.did,
            "server_pubkey": self.public_key,
            "nonce": server_nonce,
            "signature": signature,
            "timestamp": int(time.time())
        }
        print(f"   服务端随机数: {server_nonce}")
        print(f"   签名: {signature[:20]}...")
        print("📤 服务端 -> 客户端：返回握手响应")
        return response
    def step4_send_identity_result(self, identity_proof: Dict[str, Any]) -> Dict[str, Any]:
        """步骤4：返回身份验证结果"""
        print_role_separator("server")
        loading_animation("验证客户端签名有效性")
        
        # 模拟验证成功
        is_valid = True
        if is_valid:
            result = {
                "type": "identity_result",
                "success": True,
                "scopes_supported": ["goods:read", "order:create", "user:profile"],
                "token_max_ttl": 7200,
                "timestamp": int(time.time())
            }
            print("✅ 客户端身份验证通过")
            print("📤 服务端 -> 客户端：返回身份验证成功")
        else:
            result = {"type": "identity_result", "success": False, "error": "Invalid signature"}
            print("❌ 客户端身份验证失败")
        return result
    def step6_request_user_confirmation(self, scope_request: Dict[str, Any]) -> bool:
        """步骤6：向用户确认授权"""
        print_role_separator("user")
        client_info = "AI购物助手"
        scopes = scope_request["scopes"]
        
        print(f"🔔 【服务端向您确认授权请求】")
        print(f"   请求方: {client_info} ({scope_request['user_authorization']['user_id']})")
        print(f"   请求权限: {scopes}")
        print(f"   上下文: {scope_request['context']}")
        
        while True:
            choice = input("\n🤔 是否同意该授权请求？(Y/N): ").strip().upper()
            if choice == 'Y':
                loading_animation("记录用户授权结果")
                print("✅ 用户已同意授权")
                return True
            elif choice == 'N':
                print("❌ 用户拒绝授权，流程终止")
                return False
            else:
                print("⚠️  请输入Y或N")
    def step8_send_scope_result(self, user_approved: bool) -> Dict[str, Any]:
        """步骤8：返回权限审批结果"""
        print_role_separator("server")
        if user_approved:
            loading_animation("生成权限审批结果")
            result = {
                "type": "scope_result",
                "scopes_granted": ["goods:read", "order:create"],
                "ttl_granted": 7200,
                "restrictions": {
                    "rate_limit": "100/minute",
                    "ip_whitelist": ["192.168.1.0/24"]
                },
                "timestamp": int(time.time())
            }
            print(f"   授予权限: {result['scopes_granted']}")
            print(f"   有效期: {result['ttl_granted']}秒")
            print("📤 服务端 -> 客户端：返回权限审批通过")
        else:
            result = {"type": "scope_result", "success": False, "error": "User rejected"}
            print("📤 服务端 -> 客户端：返回权限审批拒绝")
        return result
    def step9_issue_access_token(self) -> str:
        """步骤9：颁发访问令牌"""
        print_role_separator("server")
        loading_animation("生成并签名访问令牌")
        token = 'ath_' + ''.join(random.choices(string.ascii_letters + string.digits, k=40))
        print(f"   令牌: {token[:20]}...")
        print("📤 服务端 -> 客户端：颁发访问令牌")
        return token
# ==================== 主流程 ====================
def main():
    print("\n" + "🎆"*30)
    print("🎆" + " "*25 + "ATH可信握手协议交互式演示" + " "*25 + "🎆")
    print("🎆"*30)
    print("\n📖 本Demo完全按照ATH协议规范实现，客户端和服务端逻辑完全独立")
    # 询问是否分开展示代码逻辑
    global show_code_separately
    while True:
        choice = input("\n🤔 是否分开展示客户端和服务端的实现逻辑？(Y/N): ").strip().upper()
        if choice == 'Y':
            show_code_separately = True
            break
        elif choice == 'N':
            show_code_separately = False
            break
        else:
            print("⚠️  请输入Y或N")
    # 1. 初始化角色
    client = Client()
    server = Server()
    # 2. 用户预授权
    if not client.get_user_authorization(["goods:read", "order:create"]):
        return
    # 3. 握手流程
    print_separator("开始9步可信握手流程")
    # 步骤1：客户端发请求
    handshake_request = client.step1_send_handshake_request()
    time.sleep(0.5)
    # 步骤2：服务端回响应
    handshake_response = server.step2_send_handshake_response(handshake_request)
    time.sleep(0.5)
    # 步骤3：客户端发身份证明
    identity_proof = client.step3_send_identity_proof(handshake_response)
    time.sleep(0.5)
    # 步骤4：服务端回验证结果
    identity_result = server.step4_send_identity_result(identity_proof)
    if not identity_result["success"]:
        return
    time.sleep(0.5)
    # 步骤5：客户端发权限请求
    scope_request = client.step5_send_scope_request()
    time.sleep(0.5)
    # 步骤6：服务端向用户确认授权
    user_approved = server.step6_request_user_confirmation(scope_request)
    if not user_approved:
        return
    time.sleep(0.5)
    # 步骤7：用户已确认，服务端处理
    time.sleep(0.5)
    # 步骤8：服务端回审批结果
    scope_result = server.step8_send_scope_result(user_approved)
    if not scope_result.get("success", True):
        return
    time.sleep(0.5)
    # 步骤9：完成握手
    access_token = server.step9_issue_access_token()
    client.step9_complete_handshake(access_token)
    # 握手完成
    print("\n" + "🎉"*30)
    print("🎉" + " "*22 + "握手流程完成！已建立可信通信通道" + " "*22 + "🎉")
    print("🎉"*30)
    # 4. 业务请求演示
    print_separator("业务请求演示")
    client.send_business_request("/api/goods?keyword=iPhone", "GET")
    time.sleep(1)
    client.send_business_request("/api/order", "POST", {"goods_id": "123", "quantity": 1, "address": "北京市朝阳区"})
    # 显示客户端和服务端代码说明
    if show_code_separately:
        print_separator("客户端和服务端实现说明")
        print("\n🔵 客户端实现（完全独立）：")
        print("   - 位于Demo文件的 [客户端实现] 部分，包含所有客户端逻辑")
        print("   - 负责：身份管理、握手请求、权限申请、加密通信")
        print("   - 可以独立提取出来作为SDK的基础实现")
        print("\n🟢 服务端实现（完全独立）：")
        print("   - 位于Demo文件的 [服务端实现] 部分，包含所有服务端逻辑")
        print("   - 负责：身份验证、授权确认、权限审批、令牌颁发")
        print("   - 可以独立提取出来作为服务端中间件的基础实现")
        print("\n📌 设计说明：")
        print("   本Demo虽然在同一个文件中运行，但客户端和服务端是完全解耦的两个类，")
        print("   两者之间只通过约定的报文格式交互，和真实网络交互完全一致。")
        print("   实际部署时，客户端和服务端会部署在不同的服务器上，通过HTTP/HTTPS通信。")
if __name__ == "__main__":
    main()
