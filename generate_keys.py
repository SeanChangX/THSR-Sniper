#!/usr/bin/env python3
"""
THSR Sniper Security Key Generator
Safely generate JWT Secret Key and Fernet Encryption Key
"""

import secrets
import os
from cryptography.fernet import Fernet


def generate_jwt_secret(length_bytes=32):
    """
    Generate JWT Secret Key
    
    Args:
        length_bytes (int): Key length in bytes, recommended 32 bytes or more
    
    Returns:
        str: URL-safe random string
    """
    return secrets.token_urlsafe(length_bytes)


def generate_fernet_key():
    """
    Generate Fernet Encryption Key
    
    Returns:
        str: Base64 encoded 32 bytes key
    """
    return Fernet.generate_key().decode()


def create_env_file(jwt_secret, encryption_key, filename='.env'):
    """
    Create .env file
    
    Args:
        jwt_secret (str): JWT secret key
        encryption_key (str): Encryption key
        filename (str): File name
    """
    env_content = f"""# Security Configuration
SECRET_KEY={jwt_secret}
ENCRYPTION_KEY={encryption_key}
"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    # Set file permissions to owner read/write only (600)
    os.chmod(filename, 0o600)
    
    return filename


def main():
    """Main function"""
    print("🔐 THSR Sniper Security Key Generator")
    print("=" * 50)
    
    # Check if .env file already exists
    if os.path.exists('.env'):
        response = input("\n⚠️  .env file already exists, overwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled")
            return
    
    print("\n📋 Generating security keys...")
    
    # Generate keys
    jwt_secret = generate_jwt_secret(32)  # 256 bits
    encryption_key = generate_fernet_key()  # 256 bits
    
    # Display generated keys
    print(f"\n✅ Key generation completed!")
    print(f"📊 JWT Secret Key: {len(jwt_secret)} characters")
    print(f"📊 Encryption Key: {len(encryption_key)} characters")
    
    # Create .env file
    env_file = create_env_file(jwt_secret, encryption_key)
    print(f"\n💾 Environment configuration file created: {env_file}")
    print(f"🔒 File permissions set to 600 (owner read/write only)")
    
    # Security reminders
    print("\n" + "=" * 50)
    print("🛡️  Security Reminders:")
    print("1. Keep these keys secure, loss will prevent decryption of existing data")
    print("2. Never commit .env file to Git version control")
    print("3. Use different keys for production environment")
    print("4. Consider rotating keys every 6-12 months")
    print("5. Re-encrypt all sensitive data after key rotation")
    
    print("\n🚀 Next Steps:")
    print("1. Verify .env file content is correct")
    print("2. Run docker-compose up -d to start services")
    print("3. Visit http://localhost:3000 to begin")
    
    # Additional configuration suggestions
    print("\n💡 Advanced Configuration Suggestions:")
    print("📝 Development: Copy .env to .env.development")
    print("📝 Production: Use key management services (e.g., AWS Secrets Manager)")
    print("📝 Docker: Use Docker Secrets or environment variable injection")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check if Python environment has cryptography package installed")
        print("Install command: pip install cryptography")
