"""
测试管理员用户登录脚本
用于诊断登录问题
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import LocalSessionLocal
from app.models import User
from app.core.security import get_password_hash, verify_password, authenticate_user

def test_admin_user():
    """测试管理员用户"""
    db = LocalSessionLocal()
    try:
        print("=" * 50)
        print("测试管理员用户")
        print("=" * 50)
        
        # 1. 检查用户是否存在
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("[ERROR] 用户 'admin' 不存在")
            print("请先运行: python scripts/create_admin.py")
            return
        
        print("[OK] 用户 'admin' 存在")
        print(f"   ID: {admin_user.id}")
        print(f"   用户名: {admin_user.username}")
        print(f"   是否激活: {admin_user.is_active}")
        print(f"   密码哈希: {admin_user.hashed_password[:50]}...")
        
        # 2. 测试密码哈希
        test_password = "admin123"
        print(f"\n测试密码: {test_password}")
        
        # 3. 测试密码验证
        print("\n测试密码验证...")
        is_valid = verify_password(test_password, admin_user.hashed_password)
        if is_valid:
            print("[OK] 密码验证成功")
        else:
            print("[ERROR] 密码验证失败")
            print(f"   存储的哈希: {admin_user.hashed_password}")
            # 重新生成哈希进行对比
            new_hash = get_password_hash(test_password)
            print(f"   新生成的哈希: {new_hash}")
            print(f"   哈希是否相同: {admin_user.hashed_password == new_hash}")
        
        # 4. 测试authenticate_user函数
        print("\n测试authenticate_user函数...")
        user = authenticate_user(db, "admin", test_password)
        if user:
            print("[OK] authenticate_user 成功")
            print(f"   返回的用户: {user.username}")
        else:
            print("[ERROR] authenticate_user 失败")
            print("   可能的原因:")
            print("   1. 用户不存在")
            print("   2. 密码错误")
            print("   3. 用户未激活")
        
        # 5. 如果验证失败，尝试重新设置密码
        if not is_valid or not user:
            print("\n" + "=" * 50)
            print("尝试重新设置密码...")
            new_hash = get_password_hash(test_password)
            admin_user.hashed_password = new_hash
            db.commit()
            print("[OK] 密码已重新设置")
            
            # 再次测试
            print("\n重新测试密码验证...")
            is_valid = verify_password(test_password, admin_user.hashed_password)
            if is_valid:
                print("[OK] 密码验证成功")
            else:
                print("[ERROR] 密码验证仍然失败")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    test_admin_user()

