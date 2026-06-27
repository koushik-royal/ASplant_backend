from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

auth_service = AuthService()
