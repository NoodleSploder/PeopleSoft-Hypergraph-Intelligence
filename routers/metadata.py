from fastapi import APIRouter

from connectors import ptmetadata

router = APIRouter(prefix="/api/metadata", tags=["PeopleTools Metadata"])


@router.get("/version")
def metadata_version(env: str = "HCM"):
    oracle_version, oracle_warning = ptmetadata.oracle_version(env)
    peopletools_version, peopletools_warning = ptmetadata.peopletools_version(env)
    schema, schema_warning = ptmetadata.current_schema(env)

    warnings = [
        item for item in (oracle_warning, peopletools_warning, schema_warning)
        if item
    ]

    return {
        "environment": env.upper(),
        "oracle_version": oracle_version,
        "peopletools_version": peopletools_version,
        "schema": schema,
        "version_adapter": ptmetadata.version_adapter(env),
        "warnings": warnings,
    }


@router.get("/capabilities")
def metadata_capabilities(env: str = "HCM"):
    return ptmetadata.capabilities(env)


@router.get("/tables")
def metadata_tables(env: str = "HCM"):
    return ptmetadata.accessible_objects(env, "TABLE")


@router.get("/views")
def metadata_views(env: str = "HCM"):
    return ptmetadata.accessible_objects(env, "VIEW")


@router.get("/cache")
def metadata_cache():
    return ptmetadata.cache_status()


@router.post("/cache/clear")
def metadata_cache_clear():
    return ptmetadata.clear_cache()


@router.get("/object-types")
def metadata_object_types():
    return ptmetadata.object_types()


@router.get("/discovery")
def metadata_discovery(env: str = "HCM"):
    return ptmetadata.discovery(env)


@router.get("/products")
def metadata_products(env: str = "HCM"):
    return ptmetadata.installed_products(env)


@router.get("/resolve/{object_type}/{name}")
def metadata_resolve(object_type: str, name: str, env: str = "HCM"):
    return ptmetadata.resolve_object(env, object_type, name)


@router.get("/capabilities/table/{table_name}")
def metadata_has_table(table_name: str, env: str = "HCM"):
    return {
        "table": table_name.upper(),
        "available": ptmetadata.has_table(env, table_name),
    }


@router.get("/capabilities/table/{table_name}/column/{column_name}")
def metadata_has_column(table_name: str, column_name: str, env: str = "HCM"):
    return {
        "table": table_name.upper(),
        "column": column_name.upper(),
        "available": ptmetadata.has_column(env, table_name, column_name),
    }


@router.get("/capabilities/view/{view_name}")
def metadata_has_view(view_name: str, env: str = "HCM"):
    return {
        "view": view_name.upper(),
        "available": ptmetadata.has_view(env, view_name),
    }
