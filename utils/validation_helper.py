def extract_validation_error_message(exc):
    detail = getattr(exc, "detail", exc)
    if isinstance(detail, dict):
        for value in detail.values():
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, dict):
                return str(value)
    if isinstance(detail, list) and detail:
        return str(detail[0])
    return str(detail)
