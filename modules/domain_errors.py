class DomainError(ValueError):
    """Safe, user-facing rejection of an invalid operation."""
    def __init__(self, message, status_code=409):
        super().__init__(message)
        self.status_code = status_code
