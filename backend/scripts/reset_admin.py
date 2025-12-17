"""
重置管理员用户密码脚本（简化版）
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import LocalSessionLocal
from app.models import User
from app.core.security import get_password_hash, verify_password

def reset_admin():
    """重置管理员密码"""
    db = LocalSessionLocal()
    try:
        print("=" * 50)
        print("重置管理员用户密码")
        print("=" * 50)
        
        # 查找用户
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            print("[ERROR] 用户 'admin' 不存在")
            print("请先运行: python scripts/create_admin.py")
            return
        
        # 设置新密码
        password = "admin123"
        print(f"设置密码: {password}")
        
        # 生成新哈希
        new_hash = get_password_hash(password)
        print(f"新密码哈希: {new_hash[:50]}...")
        
        # 更新密码
        admin_user.hashed_password = new_hash
        admin_user.is_active = True
        db.commit()
        db.refresh(admin_user)
        
        # 验证新密码
        is_valid = verify_password(password, admin_user.hashed_password)
        if is_valid:
            print("[OK] 密码重置成功并验证通过")
        else:
            print("[ERROR] 密码重置后验证失败")
            return
        
        print("=" * 50)
        print("用户名: admin")
        print("密码: admin123")
        print("=" * 50)
        print("请使用以上凭据登录")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 重置失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin()

