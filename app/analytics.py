import pandas as pd


def load_data(path):
    df = pd.read_csv(path)
    return df


def filter_data(df, country, category):
    result = df
    if country != "" and country != "Tous":
        result = result[result["country"] == country]
    if category != "" and category != "Tous":
        result = result[result["job_category"] == category]
    return result


def global_stats(df):
    stats = {}
    stats["jobs"] = len(df)
    if len(df) == 0:
        stats["avg_salary"] = 0
        stats["median_salary"] = 0
        stats["min_salary"] = 0
        stats["max_salary"] = 0
        stats["avg_demand"] = 0
        stats["remote_pct"] = 0
        stats["llm_pct"] = 0
        return stats
    stats["avg_salary"] = round(float(df["annual_salary_usd"].mean()), 2)
    stats["median_salary"] = round(float(df["annual_salary_usd"].median()), 2)
    stats["min_salary"] = round(float(df["annual_salary_usd"].min()), 2)
    stats["max_salary"] = round(float(df["annual_salary_usd"].max()), 2)
    stats["avg_demand"] = round(float(df["demand_score"].mean()), 2)
    stats["remote_pct"] = round(float(df["is_remote_friendly"].mean() * 100), 2)
    stats["llm_pct"] = round(float(df["is_llm_role"].mean() * 100), 2)
    return stats


def series_to_list(serie):
    resultat = []
    for nom in serie.index:
        resultat.append({"label": nom, "value": float(serie[nom])})
    return resultat


def salary_by_category(df):
    serie = df.groupby("job_category")["annual_salary_usd"].mean()
    serie = serie.sort_values(ascending=False).round(0)
    return series_to_list(serie)


def jobs_by_country(df):
    serie = df["country"].value_counts().head(10)
    return series_to_list(serie)


def demand_by_category(df):
    serie = df.groupby("job_category")["demand_score"].mean()
    serie = serie.sort_values(ascending=False).round(1)
    return series_to_list(serie)


def top_skills(df):
    competences = []
    for ligne in df["required_skills"]:
        for competence in ligne.split("|"):
            competences.append(competence.strip())
    serie = pd.Series(competences).value_counts().head(10)
    return series_to_list(serie)


def llm_premium(df):
    postes_llm = df[df["is_llm_role"] == 1]
    autres_postes = df[df["is_llm_role"] == 0]
    resultat = []
    if len(postes_llm) > 0:
        resultat.append({"label": "Postes LLM", "value": round(float(postes_llm["annual_salary_usd"].mean()), 0)})
    else:
        resultat.append({"label": "Postes LLM", "value": 0})
    if len(autres_postes) > 0:
        resultat.append({"label": "Autres postes", "value": round(float(autres_postes["annual_salary_usd"].mean()), 0)})
    else:
        resultat.append({"label": "Autres postes", "value": 0})
    return resultat


def job_rows(df, nombre):
    lignes = []
    for i in range(min(nombre, len(df))):
        offre = df.iloc[i]
        lignes.append({
            "job_id": offre["job_id"],
            "job_title": offre["job_title"],
            "job_category": offre["job_category"],
            "country": offre["country"],
            "experience_level": offre["experience_level"],
            "annual_salary_usd": float(offre["annual_salary_usd"]),
            "demand_score": int(offre["demand_score"]),
        })
    return lignes
