import os
import sys

dossier = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(dossier, "..", "app"))
os.environ["DATA_PATH"] = os.path.join(dossier, "..", "data", "ai_jobs_market_2025_2026.csv")

from app import app

client = app.test_client()


def test_health():
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.get_json()["status"] == "ok"


def test_stats():
    donnees = client.get("/api/stats").get_json()
    assert donnees["jobs"] == 1500
    assert round(donnees["avg_salary"]) == 194892


def test_filtre_france():
    donnees = client.get("/api/stats?country=France").get_json()
    assert donnees["jobs"] == 66


def test_page():
    reponse = client.get("/?country=France&category=Tous")
    assert reponse.status_code == 200
    assert "183 152 $" in reponse.get_data(as_text=True)
