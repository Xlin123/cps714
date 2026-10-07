from pathlib import Path

from fastapi.testclient import TestClient

from lms.app import create_app
from lms.auth import Auth
from lms.database import Database
from lms.settings import Settings


def test_client_routes_fall_back_to_index_but_api_paths_do_not(
    tmp_path: Path, settings: Settings
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<div id=root></div>")
    database = Database(settings.db_url)
    app = create_app(database, Auth(database, settings), client_dist_dir=dist)

    with TestClient(app) as client:
        assert client.get("/login").text == "<div id=root></div>"
        assert client.get("/api/does-not-exist").status_code == 404
