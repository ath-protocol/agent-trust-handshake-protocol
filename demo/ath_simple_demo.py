#!/usr/bin/env python3
"""
ATH协议极简演示Demo - SDK原生模式
不需要任何额外依赖，直接运行即可演示9步握手流程
"""
import json
import random
import string
from typing import Dict, Any
print("="*60)
print("🔗 ATH可信握手协议极简演示Demo")
print("="*60)
print("\n📋 演示场景：AI购物助手（客户端）<-> 电商平台（服务端）")
print("-"*60)
# 模拟角色
class Client:
    """客户端：AI购物助手"""
    def __init__(self):
        self.did = "did:ath:ai_shopping_assistant_001"
        self.private_key = "client_private_key_123456"
        self.public_key = "client_public_key_abcdef"
        self.user_authorization = None
        self.access_token = None
        
    def set_user_authorization(self, scopes: list):
        """用户预授权"""
        self.user_authorization = {
            "user_id": "user_001",
            "scopes": scopes,
            "signature": "user_signature_xyz"
        }
        print(f"✅ [用户] 已预授权智能体权限: {scopes}")
    def step1_send_handshake_request(self) -> Dict[str, Any]:
        """步骤1：发送握手请求"""
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        request = {
            "type": "handshake_request",
            "client_did": self.did,
            "client_pubkey": self.public_key,
            "nonce": nonce,
            "timestamp": 1717200000
        }
        print(f"\n📤 [客户端] 步骤1: 发送握手请求")
        print(f"   客户端DID: {self.did}")
        print(f"   随机数: {nonce}")
        return request
    def step3_send_identity_proof(self, server_nonce: str) -> Dict[str, Any]:
        """步骤3：发送身份证明"""
        signature = f"signature_of_{server_nonce}"
        proof = {
            "type": "identity_proof",
            "signature": signature
        }
        print(f"\n📤 [客户端] 步骤3: 发送身份证明")
        print(f"   签名: {signature[:20]}...")
        return proof
    def step5_send_scope_request(self) -> Dict[str, Any]:
        """步骤5：发送权限请求"""
        request = {
            "type": "scope_request",
            "scopes": self.user_authorization["scopes"],
            "user_authorization": self.user_authorization,
            "context": "用户需要查询商品并下单"
        }
        print(f"\n📤 [客户端] 步骤5: 发送权限请求")
        print(f"   请求权限: {request['scopes']}")
        return request
    def step9_complete_handshake(self, access_token: str):
        """步骤9：完成握手"""
        self.access_token = access_token
        print(f"\n✅ [客户端] 步骤9: 握手完成，获取访问令牌")
        print(f"   令牌: {access_token[:20]}...")
class Server:
    """服务端：电商平台"""
    def __init__(self):
        self.did = "did:ath:ecommerce_platform_001"
        self.private_key = "server_private_key_654321"
        self.public_key = "server_public_key_fedcba"
        self.client_nonce = None
        
    def step2_send_handshake_response(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """步骤2：返回握手响应"""
        self.client_nonce = request["nonce"]
        server_nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        signature = f"signature_of_{self.client_nonce}"
        response = {
            "type": "handshake_response",
            "server_did": self.did,
            "server_pubkey": self.public_key,
            "nonce": server_nonce,
            "signature": signature
        }
        print(f"\n📤 [服务端] 步骤2: 返回握手响应")
        print(f"   服务端DID: {self.did}")
        print(f"   随机数: {server_nonce}")
        return response, server_nonce
    def step4_send_identity_result(self, proof: Dict[str, Any]) -> Dict[str, Any]:
        """步骤4：返回身份验证结果"""
        print(f"\n📤 [服务端] 步骤4: 返回身份验证结果")
        print(f"   身份验证: ✅ 通过")
        return {
            "type": "identity_result",
            "success": True,
            "scopes_supported": ["goods:read", "order:create", "user:profile"]
        }
    def step6_send_authorization_confirm(self, scope_request: Dict[str, Any]):
        """步骤6：向用户确认授权"""
        print(f"\n📤 [服务端] 步骤6: 向用户确认授权")
        print(f"   【授权请求】AI购物助手请求权限: {scope_request['scopes']}")
        
    def step8_send_scope_result(self, user_approved: bool) -> Dict[str, Any]:
        """步骤8：返回权限审批结果"""
        if user_approved:
            result = {
                "type": "scope_result",
                "scopes_granted": ["goods:read", "order:create"],
                "ttl_granted": 7200
            }
            print(f"\n📤 [服务端] 步骤8: 返回权限审批结果")
            print(f"   审批结果: ✅ 同意，授予权限: {result['scopes_granted']}")
            return result
        else:
            return {"type": "scope_result", "success": False}
    def step9_issue_token(self) -> str:
        """步骤9：颁发访问令牌"""
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        print(f"\n📤 [服务端] 步骤9: 颁发访问令牌")
        return token
# 演示流程
def run_demo():
    print("\n🚀 开始演示ATH协议9步握手流程...\n")
    
    # 初始化角色
    client = Client()
    server = Server()
    
    # 前置步骤：用户预授权
    client.set_user_authorization(["goods:read", "order:create"])
    
    # 步骤1：客户端 -> 服务端 握手请求
    handshake_request = client.step1_send_handshake_request()
    
    # 步骤2：服务端 -> 客户端 握手响应
    handshake_response, server_nonce = server.step2_send_handshake_response(handshake_request)
    
    # 步骤3：客户端 -> 服务端 身份证明
    identity_proof = client.step3_send_identity_proof(server_nonce)
    
    # 步骤4：服务端 -> 客户端 身份验证结果
    identity_result = server.step4_send_identity_result(identity_proof)
    
    # 步骤5：客户端 -> 服务端 权限请求
    scope_request = client.step5_send_scope_request()
    
    # 步骤6：服务端 -> 用户 授权确认
    server.step6_send_authorization_confirm(scope_request)
    
    # 步骤7：用户 -> 服务端 授权确认结果（模拟用户点击同意）
    user_approved = True
    print(f"\n✅ [用户] 步骤7: 同意授权请求")
    
    # 步骤8：服务端 -> 客户端 权限审批结果
    scope_result = server.step8_send_scope_result(user_approved)
    
    # 步骤9：完成握手，建立会话
    access_token = server.step9_issue_token()
    client.step9_complete_handshake(access_token)
    
    print("\n" + "="*60)
    print("🎉 握手流程完成！AI助手现在可以访问电商平台API了")
    print("="*60)
    
    # 模拟业务请求
    print("\n📦 演示业务请求：查询商品")
    print(f"GET /api/goods?keyword=手机")
    print(f"Authorization: Bearer {access_token[:20]}...")
    print("✅ 请求成功，返回商品列表")
    
    print("\n📦 演示业务请求：创建订单")
    print(f"POST /api/order {{'goods_id': '123', 'quantity': 1}}")
    print(f"Authorization: Bearer {access_token[:20]}...")
    print("✅ 请求成功，订单已创建")
if __name__ == "__main__":
    run_demo()
