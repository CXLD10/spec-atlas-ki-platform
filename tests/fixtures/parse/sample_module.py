def build_token(user_id: str) -> str:
    return f"token:{user_id}"


class TokenVerifier:
    def verify(self, token: str) -> bool:
        return token.startswith("token:")
