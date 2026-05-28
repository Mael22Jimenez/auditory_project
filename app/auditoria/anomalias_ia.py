import pandas as pd
import numpy as np


# ==========================================
# 🔹 DETECCION DE ANOMALIAS (MEJORADA)
# ==========================================
def detectar_anomalias(df: pd.DataFrame, inconsistencias=None):

    columnas_numericas = df.select_dtypes(include=["int64", "float64"])

    if columnas_numericas.empty:
        return []

    X = columnas_numericas.fillna(columnas_numericas.median())

    media = X.mean()
    std = X.std().replace(0, 1)
    z_scores = (X - media) / std

    Q1 = X.quantile(0.25)
    Q3 = X.quantile(0.75)
    IQR = Q3 - Q1

    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR

    filas_con_error = set()

    if inconsistencias:
        for inc in inconsistencias:
            filas_con_error.add(int(inc.get("fila", -1)))

    anomalias = []

    for idx in range(len(X)):

        columnas_outlier = []
        score_total = 0

        for col in X.columns:

            valor = X.iloc[idx][col]
            z = abs(z_scores.iloc[idx][col])

            fuera_iqr = valor < lower[col] or valor > upper[col]

            if z > 2 or fuera_iqr:

                columnas_outlier.append(col)
                score_total += z

        if columnas_outlier:

            fila_real = int(df.iloc[idx]["_excel_row"]) if "_excel_row" in df.columns else idx

            tiene_error = fila_real in filas_con_error

            # 🔥 percentil (nuevo)
            percentiles = []
            for col in columnas_outlier:
                percentil = (X[col] < X.iloc[idx][col]).mean() * 100
                percentiles.append(round(percentil, 2))

            percentil_promedio = round(np.mean(percentiles), 2) if percentiles else 0

            # 🔥 severidad mejorada
            if tiene_error:
                tipo = "Anomalia sobre inconsistencia"
                severidad = "Crítica"
            else:
                tipo = "Anomalia estadística"

                if score_total > 15:
                    severidad = "Alta"
                elif score_total > 8:
                    severidad = "Media"
                else:
                    severidad = "Baja"

            anomalias.append({
                "fila": fila_real,
                "tipo": tipo,
                "columnas_afectadas": ", ".join(columnas_outlier),
                "descripcion": f"Outliers detectados en {len(columnas_outlier)} columnas",
                "score": round(float(score_total), 2),
                "percentil": percentil_promedio,
                "tiene_inconsistencia": tiene_error,
                "severidad": severidad
            })

    return anomalias


# ==========================================
# 🔹 ESTADISTICAS GENERALES
# ==========================================
def generar_estadisticas(df: pd.DataFrame):

    resultados = {}

    
    columnas_excluir = ["_excel_row"]

    num_df = df.select_dtypes(include=["int64", "float64"]) \
            .drop(columns=[col for col in columnas_excluir if col in df.columns], errors="ignore")


    if not num_df.empty:
        desc = num_df.describe(percentiles=[0.25, 0.5, 0.75]).T

        desc["std"] = num_df.std()
        desc["skewness"] = num_df.skew()
        desc["kurtosis"] = num_df.kurt()

        resultados["resumen_numerico"] = desc.round(2).to_dict(orient="index")

    # ==================================
    # 🔹 CALIDAD DE DATOS
    # ==================================
    calidad = []

    for col in df.columns:

        total = len(df)
        nulos = df[col].isna().sum()
        unicos = df[col].nunique()

        calidad.append({
            "columna": col,
            "nulos": int(nulos),
            "porcentaje_nulos": round(nulos / total * 100, 2),
            "valores_unicos": int(unicos),
            "porcentaje_unicos": round(unicos / total * 100, 2)
        })

    resultados["calidad_datos"] = calidad

    # ==================================
    # 🔹 DUPLICADOS
    # ==================================
    resultados["duplicados"] = int(df.duplicated().sum())

    # ==================================
    # 🔹 CORRELACIONES
    # ==================================
    correlaciones_altas = []

    if not num_df.empty:

        corr = num_df.corr()

        for col in corr.columns:
            for idx in corr.index:
                if col != idx:
                    val = corr.loc[idx, col]

                    if abs(val) > 0.8:
                        correlaciones_altas.append({
                            "columna_1": col,
                            "columna_2": idx,
                            "correlacion": round(val, 2)
                        })

    resultados["correlaciones_fuertes"] = correlaciones_altas

    return resultados


# ==========================================
# 🔹 GENERADOR DE INSIGHTS AUTOMATICOS
# ==========================================
def generar_insights_completo(estadisticas, analisis_inc):

    insights = []

    # =========================
    # 🔹 1. CALIDAD DE DATOS (USA estadisticas ✅)
    # =========================
    calidad = estadisticas.get("calidad_datos", [])

    if calidad:
        top_nulos = sorted(
            calidad,
            key=lambda x: x["porcentaje_nulos"],
            reverse=True
        )

        if top_nulos and top_nulos[0]["porcentaje_nulos"] > 0:
            insights.append(
                f"La columna '{top_nulos[0]['columna']}' tiene mayor porcentaje de nulos ({top_nulos[0]['porcentaje_nulos']}%)"
            )

    # =========================
    # 🔹 2. VARIABILIDAD ALTA (estadisticas ✅)
    # =========================
    resumen = estadisticas.get("resumen_numerico", {})

    if resumen:
        col_max_std = max(resumen.items(), key=lambda x: x[1].get("std", 0))

        insights.append(
            f"La columna '{col_max_std[0]}' presenta mayor variabilidad (std={col_max_std[1]['std']})"
        )

    # =========================
    # 🔹 3. COLUMNAS CON MAS ERRORES (analisis_inc ✅)
    # =========================
    cols = analisis_inc.get("columnas_problematicas", {})

    if cols:
        top = max(cols.items(), key=lambda x: x[1])

        insights.append(
            f"La columna '{top[0]}' es la más propensa a errores ({top[1]} fallas)"
        )

    # =========================
    # 🔹 4. OWNER CON MAS ERRORES
    # =========================
    owners = analisis_inc.get("por_owner", {})

    if owners:
        top = max(owners.items(), key=lambda x: x[1])

        insights.append(
            f"El owner '{top[0]}' concentra más inconsistencias ({top[1]})"
        )

    # =========================
    # 🔹 5. REGLA MAS PROBLEMATICA
    # =========================
    reglas = analisis_inc.get("por_regla", {})

    if reglas:
        top = max(reglas.items(), key=lambda x: x[1])

        insights.append(
            f"La regla '{top[0]}' genera más inconsistencias ({top[1]})"
        )

    return insights



def analizar_inconsistencias(inconsistencias):

    if not inconsistencias:
        return {}

    df_inc = pd.DataFrame(inconsistencias)

    resultados = {}

    # =========================
    # 🔹 POR REGLA
    # =========================
    if "regla_id" in df_inc.columns:
        resultados["por_regla"] = (
            df_inc["regla_id"]
            .value_counts()
            .to_dict()
        )

    # =========================
    # 🔹 POR OWNER
    # =========================
    if "owner" in df_inc.columns:
        resultados["por_owner"] = (
            df_inc["owner"]
            .value_counts()
            .to_dict()
        )

    # =========================
    # 🔹 POR SEVERIDAD
    # =========================
    if "severidad" in df_inc.columns:
        resultados["por_severidad"] = (
            df_inc["severidad"]
            .value_counts()
            .to_dict()
        )

    # =========================
    # 🔹 CAMPOS MAS FALLADOS
    # =========================
    columnas_error = []

    for inc in inconsistencias:
        if "campo_error_1" in inc:
            columnas_error.append(inc["campo_error_1"])
        if "campo_error_2" in inc:
            columnas_error.append(inc.get("campo_error_2"))

        if "columnas_faltantes" in inc:
            columnas_error.extend(
                inc["columnas_faltantes"].split(", ")
            )

    if columnas_error:
        resultados["columnas_problematicas"] = (
            pd.Series(columnas_error)
            .value_counts()
            .to_dict()
        )

    # =========================
    # 🔹 TOP PRODUCTOS
    # =========================
    if "producto" in df_inc.columns:
        resultados["top_productos"] = (
            df_inc["producto"]
            .value_counts()
            .head(10)
            .to_dict()
        )

    return resultados



def ejecutar_analisis_completo(df, inconsistencias=None):

    
        anomalias = detectar_anomalias(df, inconsistencias)

        estadisticas = generar_estadisticas(df)

        analisis_inc = analizar_inconsistencias(inconsistencias) 

        insights = generar_insights_completo(estadisticas, analisis_inc)  

        return {
            "anomalias": anomalias,
            "estadisticas": estadisticas,
            "analisis_inconsistencias": analisis_inc,  # opcional pero recomendado
            "insights": insights
        }



