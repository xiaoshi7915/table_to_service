"""
创建管理员用户脚本
"""
import sys
from database import LocalSessionLocal
from models import User
from auth import get_password_hash

def create_admin_user():
    """创建管理员用户"""
    db = LocalSessionLocal()
    try:
        # 检查是否已存在用户
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print(f"用户 'admin' 已存在")
            print(f"如果需要重置密码，请删除用户后重新运行此脚本")
            return
        
        # 创建默认管理员用户
        password = "admin123"
        hashed_password = get_password_hash(password)
        admin_user = User(
            username="admin",
            hashed_password=hashed_password,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        
        print("=" * 50)
        print("管理员用户创建成功！")
        print("=" * 50)
        print("用户名: admin")
        print("密码: admin123")
        print("=" * 50)
        print("⚠️  请登录后立即修改密码！")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"创建用户失败: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()

