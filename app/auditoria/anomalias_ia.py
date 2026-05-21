import pandas as pd
from sklearn.ensemble import IsolationForest


def detectar_anomalias(df: pd.DataFrame):
    columnas_numericas = df.select_dtypes(include=["int64", "float64"])

    if columnas_numericas.empty:
        return []

    X = columnas_numericas.fillna(columnas_numericas.median())

    modelo = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )

    modelo.fit(X)

    scores = modelo.decision_function(X)
    predicciones = modelo.predict(X)

    anomalias = []

    for idx, pred in enumerate(predicciones):
        if pred == -1:
            anomalias.append({
                "fila": idx,
                "score": round(float(scores[idx]), 4),
                "tipo": "Anomalia estadistica",
                "descripcion": "Registro con comportamiento atipico",
                "severidad": "alta"
            })

   
    return anomalias
