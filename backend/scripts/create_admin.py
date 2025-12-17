"""
创建管理员用户脚本
"""
import sys
from pathlib import Path

# 添加backend目录到Python路径
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import LocalSessionLocal
from app.models import User
from app.core.security import get_password_hash

def create_admin_user(reset_password=False):
    """创建管理员用户"""
    db = LocalSessionLocal()
    try:
        # 检查是否已存在用户
        existing_user = db.query(User).filter(User.username == "admin").first()
        
        # 默认密码
        password = "admin123"
        
        if existing_user:
            if reset_password:
                # 重置密码
                print("=" * 50)
                print("重置管理员用户密码")
                print("=" * 50)
                hashed_password = get_password_hash(password)
                existing_user.hashed_password = hashed_password
                existing_user.is_active = True
                db.commit()
                db.refresh(existing_user)
                
                print("[OK] 密码重置成功！")
                print("=" * 50)
                print("用户名: admin")
                print("密码: admin123")
                print("=" * 50)
                print("请登录后立即修改密码！")
                print("=" * 50)
            else:
                print("=" * 50)
                print(f"用户 'admin' 已存在")
                print("=" * 50)
                print(f"用户ID: {existing_user.id}")
                print(f"是否激活: {existing_user.is_active}")
                print(f"密码哈希: {existing_user.hashed_password[:50]}...")
                print("=" * 50)
                print("如果需要重置密码，请运行:")
                print("  python scripts/create_admin.py --reset")
                print("=" * 50)
            return
        
        # 创建默认管理员用户
        print("=" * 50)
        print("创建管理员用户")
        print("=" * 50)
        
        hashed_password = get_password_hash(password)
        print(f"密码哈希生成成功: {hashed_password[:50]}...")
        
        admin_user = User(
            username="admin",
            hashed_password=hashed_password,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("[OK] 管理员用户创建成功！")
        print("=" * 50)
        print("用户名: admin")
        print("密码: admin123")
        print(f"用户ID: {admin_user.id}")
        print("=" * 50)
        print("请登录后立即修改密码！")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print("=" * 50)
        print(f"[ERROR] 创建用户失败: {e}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="创建或重置管理员用户")
    parser.add_argument("--reset", action="store_true", help="重置现有用户的密码")
    args = parser.parse_args()
    
    create_admin_user(reset_password=args.reset)

