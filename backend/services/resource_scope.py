"""Fail-closed SQL resource visibility scopes."""

def build_resource_scope(alias, allowed_resources):
    """
    Return a SQL predicate requiring access to every linked resource.

    Legacy records without accessed_resources rows are supported only
    when their complete resource value exactly matches an allowed name.
    """
    normalized = sorted({
        str(resource).strip().lower()
        for resource in allowed_resources
        if resource and str(resource).strip()
    })

    if not normalized:
        return None, []

    placeholders = ", ".join(["%s"] * len(normalized))

    linked_scope = f"""
        (
            EXISTS (
                SELECT 1
                FROM accessed_resources AS scope_ar
                WHERE scope_ar.log_id = {alias}.log_id
            )
            AND NOT EXISTS (
                SELECT 1
                FROM accessed_resources AS scope_ar
                LEFT JOIN resources AS scope_r
                    ON scope_r.resource_id = scope_ar.resource_id
                WHERE scope_ar.log_id = {alias}.log_id
                  AND (
                      scope_r.resource_id IS NULL
                      OR LOWER(scope_r.resource_name)
                          NOT IN ({placeholders})
                  )
            )
        )
    """

    legacy_scope = f"""
        (
            NOT EXISTS (
                SELECT 1
                FROM accessed_resources AS scope_ar
                WHERE scope_ar.log_id = {alias}.log_id
            )
            AND LOWER({alias}.resource) IN ({placeholders})
        )
    """

    return (
        f"({linked_scope} OR {legacy_scope})",
        normalized + normalized,
    )
