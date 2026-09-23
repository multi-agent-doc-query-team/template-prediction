from app.api.routers.template_routes import health_check


def test_health_check():
    assert health_check() == {
        "status": "healthy",
        "message": "Template Selection API is operational.",
    }
