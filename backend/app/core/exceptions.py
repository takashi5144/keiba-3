"""
カスタム例外クラス
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class AppException(Exception):
    """アプリケーション基底例外"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """リソース未発見エラー"""
    
    def __init__(self, resource: str, resource_id: Optional[str] = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )


class ValidationError(AppException):
    """バリデーションエラー"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class ScrapingError(AppException):
    """スクレイピングエラー"""
    
    def __init__(self, message: str, url: Optional[str] = None):
        details = {"url": url} if url else {}
        super().__init__(
            message=f"Scraping failed: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class DatabaseError(AppException):
    """データベースエラー"""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        details = {"operation": operation} if operation else {}
        super().__init__(
            message=f"Database error: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class AuthenticationError(AppException):
    """認証エラー"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(AppException):
    """認可エラー"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


class RateLimitError(AppException):
    """レート制限エラー"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


class ExternalServiceError(AppException):
    """外部サービスエラー"""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error ({service}): {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"service": service}
        )


def create_http_exception(exc: AppException) -> HTTPException:
    """
    カスタム例外からHTTPExceptionを生成
    
    Args:
        exc: カスタム例外
        
    Returns:
        HTTPException: FastAPIのHTTP例外
    """
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "message": exc.message,
            "type": exc.__class__.__name__,
            **exc.details
        }
    )