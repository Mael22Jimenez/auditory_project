import os
import pandas as pd
from datetime import datetime


# ===============================
# LECTURA DE ARCHIVOS
# ===============================
def leer_archivo(ruta_archivo: str) -> pd.DataFrame:
    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError("El archivo no existe")

    extension = os.path.splitext(ruta_archivo)[1].lower()

    if extension == ".csv":
        return pd.read_csv(
            ruta_archivo,
            sep=";",
            decimal=",",
            encoding="utf-8"
        )

    if extension == ".xlsx":
        df = pd.read_excel(
            ruta_archivo,
            engine="openpyxl",
            dtype=str,
            keep_default_na=False
        )
        df = df.astype(str)

        return df

    raise ValueError("Formato no soportado. Use .xlsx o .csv")


# ===============================
# LIMPIEZA BÁSICA
# ===============================
def limpiar_datos_basico(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.dropna(how="all", inplace=True)
    df.columns = [col.strip() for col in df.columns]
    return df


# ===============================
# INSPECCIÓN
# ===============================
def inspeccionar_estructura(df: pd.DataFrame) -> dict:
    return {
        "total_columnas": len(df.columns),
        "nombres_columnas": list(df.columns),
        "total_filas": len(df),
        "columnas_con_nulos": df.columns[df.isna().any()].tolist(),
        "tipo_datos": df.dtypes.astype(str).to_dict()
    }


# ===============================
# PIPELINE PRINCIPAL
# ===============================
def preparar_datos(ruta_archivo: str) -> dict:

    df = leer_archivo(ruta_archivo)

    # Agregar número de fila Excel antes de cualquier limpieza
    df["_excel_row"] = df.index + 2

    df = limpiar_datos_basico(df)


    # Columnas de fecha con sus nombres originales (antes de normalizar)
    columnas_fecha_originales = [
        "Order date",
        "Deliv.date",
        "Rev.deliv. date",
        "ETD",
        "Updated time stamp"
    ]

 
   
   
   
    def parse_fecha_segura(valor):

        # ✅ 1. nulos
        if pd.isna(valor):
            return pd.NaT

        # ✅ 2. convertir todo a string limpio
        valor_str = str(valor).strip()

        valor_str = (
            valor_str
            .replace("\xa0", "")
            .replace("\n", "")
            .replace("\r", "")
            .replace("\t", "")
        )

        # ✅ quitar hora si existe
        if " " in valor_str:
            valor_str = valor_str.split(" ")[0]

        # ✅ intentar detectar formato ISO (YYYY-MM-DD)
        if "-" in valor_str and valor_str.count("-") == 2:
            try:
                anio, mes, dia = valor_str.split("-")

                anio = int(anio)
                mes = int(mes)
                dia = int(dia)

                # ✅ CLAVE: reconstruir MM/DD (por error de Excel)
                return datetime(anio, dia, mes)

            except:
                return pd.NaT

        # ✅ normalizar separador
        valor_str = valor_str.replace("-", "/")

        # ✅ formato MM/DD/YYYY
        try:
            partes = valor_str.split("/")

            if len(partes) == 3:
                mes = int(partes[0])
                dia = int(partes[1])
                anio = int(partes[2])

                if anio < 100:
                    anio += 2000

                return datetime(anio, mes, dia)

        except:
            return pd.NaT

        return pd.NaT



    
    
    for col in columnas_fecha_originales:
        if col in df.columns:

            # ✅ aplicar SIEMPRE
            df[col] = df[col].apply(parse_fecha_segura)

            # ✅ limpiar hora
            df[col] = df[col].apply(
                lambda x: x.replace(hour=0, minute=0, second=0, microsecond=0)
                if isinstance(x, datetime)
                else x
            )



    # Eliminar filas sin claves principales (antes de normalizar nombres)
    columnas_clave = ["VendorID", "OrderNo", "Product"]
    existentes = [c for c in columnas_clave if c in df.columns]
    if existentes:
        df = df.dropna(subset=existentes, how="any")

    # Ahora sí normalizar nombres de columna (minúsculas, sin espacios ni puntos)
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
    )


    df = df.reset_index(drop=True)

    estructura = inspeccionar_estructura(df)

    return {
        "dataframe": df,
        "estructura": estructura
    }


# ===============================
# METADATA
# ===============================
def obtener_metadata(df, filename):
    return {
        "filename": filename,
        "rows": len(df),
        "columns": len(df.columns)
    }