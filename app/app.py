import os
import socket
import time

from flask import Flask, jsonify, render_template, request

import analytics

DATA_PATH = os.getenv("DATA_PATH", "/app/data/ai_jobs_market_2025_2026.csv")
CLUSTER_NAME = os.getenv("CLUSTER_NAME", "local")
POD_NAME = os.getenv("POD_NAME", socket.gethostname())
NODE_NAME = os.getenv("NODE_NAME", "local")
APP_TITLE = os.getenv("APP_TITLE", "AI Jobs Market Dashboard")

app = Flask(__name__)
df = analytics.load_data(DATA_PATH)


def format_nombre(valeur):
    texte = "{:,.0f}".format(valeur)
    return texte.replace(",", " ")


app.jinja_env.filters["nombre"] = format_nombre


def ecrire_log(route, debut, code):
    duree = round((time.time() - debut) * 1000, 1)
    date = time.strftime("%Y-%m-%d %H:%M:%S")
    print(date, route, "cluster=" + CLUSTER_NAME, "pod=" + POD_NAME, "status=" + str(code), "duree_ms=" + str(duree), flush=True)


@app.get("/health")
def health():
    return {"status": "ok"}, 200


@app.get("/api/stats")
def stats():
    debut = time.time()
    pays = request.args.get("country", "")
    categorie = request.args.get("category", "")
    donnees = analytics.filter_data(df, pays, categorie)
    resultat = analytics.global_stats(donnees)
    resultat["cluster"] = CLUSTER_NAME
    resultat["pod"] = POD_NAME
    resultat["node"] = NODE_NAME
    ecrire_log("/api/stats", debut, 200)
    return jsonify(resultat)


@app.get("/api/jobs")
def jobs():
    debut = time.time()
    pays = request.args.get("country", "")
    categorie = request.args.get("category", "")
    donnees = analytics.filter_data(df, pays, categorie)
    lignes = analytics.job_rows(donnees, 50)
    ecrire_log("/api/jobs", debut, 200)
    return jsonify(lignes)


@app.get("/")
def index():
    debut = time.time()
    pays = request.args.get("country", "Tous")
    categorie = request.args.get("category", "Tous")
    donnees = analytics.filter_data(df, pays, categorie)

    liste_pays = sorted(df["country"].unique())
    liste_categories = sorted(df["job_category"].unique())

    graphiques = {}
    graphiques["salaire_categorie"] = analytics.salary_by_category(donnees)
    graphiques["offres_pays"] = analytics.jobs_by_country(donnees)
    graphiques["demande_categorie"] = analytics.demand_by_category(donnees)
    graphiques["competences"] = analytics.top_skills(donnees)
    graphiques["llm"] = analytics.llm_premium(donnees)

    page = render_template(
        "index.html",
        titre=APP_TITLE,
        cluster=CLUSTER_NAME,
        pod=POD_NAME,
        node=NODE_NAME,
        stats=analytics.global_stats(donnees),
        lignes=analytics.job_rows(donnees, 20),
        graphiques=graphiques,
        liste_pays=liste_pays,
        liste_categories=liste_categories,
        pays=pays,
        categorie=categorie,
    )
    ecrire_log("/", debut, 200)
    return page


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
