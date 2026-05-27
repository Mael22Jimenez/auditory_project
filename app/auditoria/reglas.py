import json
import os
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_REGLAS = os.path.join(BASE_DIR, "reglas_config.json")



def cargar_reglas():
    with open(RUTA_REGLAS, "r", encoding="utf-8") as f:
        return json.load(f)


def ejecutar_reglas(df, bases_data, reglas_activas, tipo_auditoria=None):
        
        print("🔥 BASES_DATA CONTENT:", bases_data, flush=True)

        
        inventory_key = None

        for key in bases_data:
            if "invent" in key.lower():
                inventory_key = key
                break

        if inventory_key:

            df_inv = pd.read_excel(bases_data[inventory_key])


            inventory_key = None

            for key in bases_data:
                if "invent" in key.lower():
                    inventory_key = key
                    break

            if inventory_key:
                df_inv = pd.read_excel(bases_data[inventory_key])
            else:
                df_inv = None


            df_inv.columns = df_inv.columns.str.strip().str.lower()
            
            df.columns = (
                df.columns
                .str.strip()
                .str.lower()
                .str.replace(" ", "", regex=False)
            )

            
            if "product" not in df.columns and "newcode" in df.columns:
                df["product"] = df["newcode"]

            if "owner" not in df.columns and "planner" in df.columns:
                df["owner"] = df["planner"]


            def clean_key(x):
                x = str(x).upper().strip()
                x = x.replace("-", "").replace(" ", "")
                return x

            df["product_key"] = df["product"].apply(clean_key)
            df_inv["item_key"] = df_inv["item"].apply(clean_key)

                        
            print("=== DEBUG BEFORE MERGE ===")
            print("DF PRODUCT SAMPLE:")
            print(df["product"].head(10))

            print("INV ITEM SAMPLE:")
            print(df_inv["item"].head(10))

            
            df = df.merge(
                df_inv[["item_key", "owner"]],
                left_on="product_key",
                right_on="item_key",
                how="left"
            )

        
    
            if tipo_auditoria == "datos_faltantes" and "planner" in df.columns:
                
                df["owner"] = df["planner"]

                df["owner"] = df["owner"].astype(str).str.strip()
                df["owner"] = df["owner"].replace("", "SIN OWNER")

            else:
                df["owner"] = df["owner"].astype(str).str.strip()
                df["owner"] = df["owner"].replace("", "SIN OWNER")


                        
            print("=== DEBUG AFTER MERGE ===")
            print("TOTAL ROWS:", len(df))
            print("OWNER NULL COUNT:", df["owner"].isna().sum())

            print(df[["product", "product_key", "item_key", "owner"]].head(20))


        reglas = cargar_reglas()
        inconsistencias = []

        for regla in reglas:

            if not regla.get("activa", False):
                continue

            if regla["id"] not in reglas_activas:
                continue

            tipo = regla.get("tipo")

            if tipo == "fecha_menor":
                inconsistencias.extend(regla_fecha_menor(df, regla))

            elif tipo == "fecha_mayor":
                inconsistencias.extend(regla_fecha_mayor(df, regla))

            elif tipo == "etd_vacia":
                inconsistencias.extend(regla_etd_vacia(df, regla))

            elif tipo == "lead_time_correcto":
                inconsistencias.extend(regla_leadtime(df, regla))

            elif tipo == "leadtime_vs_base":
                inconsistencias.extend(
                    regla_leadtime_vs_base(df, regla, bases_data))

            elif tipo == "lifecycle_time":
                inconsistencias.extend(
                    regla_lifecycle_new_current(df, regla, bases_data))

            elif tipo == "datos_faltantes":
                inconsistencias.extend(regla_datos_faltantes(df, regla))
               

        inconsistencias_unicas = []
        seen = set()

        for inc in inconsistencias:
            key = (
                inc.get("fila"),
                inc.get("regla_id"),
                inc.get("producto"),
                inc.get("mensaje")
            )

            if key not in seen:
                seen.add(key)
                inconsistencias_unicas.append(inc)

        return inconsistencias_unicas



        return inconsistencias




def regla_fecha_menor(df, regla):

    col_entrega = regla["columnas"][0].lower().replace(" ", "").replace(".", "")
    col_orden = regla["columnas"][1].lower().replace(" ", "").replace(".", "")

    inconsistencias = []

    if col_entrega not in df.columns or col_orden not in df.columns:
        return inconsistencias

    for _, row in df.iterrows():

        producto = str(row["product"]).strip().upper()
        orderNo = str(row["orderno"]).strip().upper()

        owner = str(row.get("owner", "")).strip().upper() or "SIN OWNER"

        if pd.notna(row[col_entrega]) and pd.notna(row[col_orden]):
            if row[col_entrega] < row[col_orden]:

                inconsistencias.append({
                    "regla_id": regla["id"],
                    "fila": int(row["_excel_row"]),
                    "producto": producto,
                    "orderNo": orderNo,
                    "fechaEntrega": str(row[col_entrega]),
                    "fechaOrden": str(row[col_orden]),
                    "owner": owner,

                    
    

                    "mensaje": regla["descripcion"],
                    "severidad": regla["severidad"]
                })

    return inconsistencias






def regla_fecha_mayor(df, regla):

    col1 = regla["columnas"][0].lower().replace(" ", "").replace(".", "")
    col2 = regla["columnas"][1].lower().replace(" ", "").replace(".", "")

    inconsistencias = []

    if col1 not in df.columns or col2 not in df.columns:
        return inconsistencias

    for _, row in df.iterrows():

        producto = str(row["product"]).strip().upper()
        orderNo = str(row["orderno"]).strip().upper()

        owner = str(row.get("owner", "")).strip().upper() or "SIN OWNER"

        if pd.notna(row[col1]) and pd.notna(row[col2]):
            if row[col1] > row[col2]:

                inconsistencias.append({
                    "regla_id": regla["id"],
                    "fila": int(row["_excel_row"]),
                    "producto": producto,
                    "orderNo": orderNo,
                    "etd": str(row[col1]),
                    "fechaEntrega": str(row[col2]) ,
                    "owner": owner,

                    
                    "campo_error_1": col1,
                    "campo_error_2": col2,

                    "mensaje": regla["descripcion"],
                    "severidad": regla["severidad"]
                })

    return inconsistencias





def regla_etd_vacia(df, regla):

    col_etd = regla["columnas"][0].lower().replace(" ", "").replace(".", "")

    inconsistencias = []

    if col_etd not in df.columns:
        return inconsistencias

    for _, row in df.iterrows():

        producto = str(row["product"]).strip().upper()
        orderNo = str(row["orderno"]).strip().upper()

        owner = str(row.get("owner", "")).strip().upper() or "SIN OWNER"

        if pd.isna(row[col_etd]):

            inconsistencias.append({
                "regla_id": regla["id"],
                "fila": int(row["_excel_row"]),
                "producto": producto,
                "orderNo": orderNo,
                "etd": None,
                "owner": owner,

                "campo_error_1": col_etd,

                "mensaje": regla["descripcion"],
                "severidad": regla["severidad"]
            })

    return inconsistencias





def regla_leadtime(df, regla):

    col1 = regla["columnas"][0].lower().replace(" ", "").replace(".", "")
    col2 = regla["columnas"][1].lower().replace(" ", "").replace(".", "")

    inconsistencias = []

    if col1 not in df.columns or col2 not in df.columns:
        return inconsistencias

    for _, row in df.iterrows():

        producto = str(row["product"]).strip().upper()
        orderNo = str(row["orderno"]).strip().upper()

        owner = str(row.get("owner", "")).strip().upper() or "SIN OWNER"

        if pd.notna(row[col1]) and pd.notna(row[col2]):
            if row[col1] <= 0 or row[col2] <= 0:

                inconsistencias.append({
                    "regla_id": regla["id"],
                    "fila": int(row["_excel_row"]),
                    "producto": producto,
                    "orderNo": orderNo,
                    "owner": owner,

                    
                    "campo_error_1": col1,
                    "campo_error_2": col2,

                    "mensaje": regla["descripcion"],
                    "severidad": regla["severidad"]
                })

    return inconsistencias





def regla_leadtime_vs_base(df, regla, bases_data):

    print("✅ INICIANDO REGLA LT_04")

    base_path = bases_data.get("LeadTime")

    if not base_path:
        print("❌ NO HAY BASE LeadTime")
        return []

    inconsistencias = []

    # ===============================
    # 🔹 DEBUG INICIAL (NO ROMPE)
    # ===============================
    if "owner" in df.columns:
        print("OWNER OK:", df["owner"].notna().sum())
    else:
        print("❌ DF SIN OWNER")

    # ===============================
    # 🔹 LEER BASE
    # ===============================
    df_dict = pd.read_excel(base_path, sheet_name=None)

    dfs_validos = []

    for name, df_sheet in df_dict.items():

        df_sheet["_source"] = name

        cols = (
            df_sheet.columns
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(" ", "", regex=False)
            .str.replace("-", "", regex=False)
        )

        if "newleadtimelogistics" in cols.tolist():
            dfs_validos.append(df_sheet)

    if not dfs_validos:
        return []

    df_base = pd.concat(dfs_validos, ignore_index=True)

    df_base.columns = (
        df_base.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "", regex=False)
        .str.replace("-", "", regex=False)
    )

    if "product" not in df_base.columns:
        return []


    df_base["product"] = df_base["product"].astype(str).str.strip().str.upper()

    # ===============================
    # 🔹 BASE MAP ORIGINAL 
    # ===============================
    base_map = {}

    for _, row_base in df_base.iterrows():

        producto_base = str(row_base["product"]).strip().upper()

        if "company" not in df_base.columns:
            continue

        company_base = str(row_base["company"]).strip().upper()

        key = (company_base, producto_base)

        valor_new = row_base.get("newleadtimelogistics")
        origen = row_base.get("_source")

        
        if isinstance(valor_new, pd.Series):
            valores_lista = valor_new.dropna().tolist()
        else:
            valores_lista = [valor_new]

        for val in valores_lista:

            if pd.notna(val):
                try:
                    val = float(val)

                    if val > 0:

                        if key not in base_map:
                            base_map[key] = []

                        # ✅ evitar duplicados exactos
                        if not any(d["valor"] == val for d in base_map[key]):
                            base_map[key].append({
                                "valor": val,
                                "fuente": origen
                            })

                except:
                    continue

    print("✅ TOTAL PRODUCTOS BASE:", len(base_map))

    # ===============================
    # 🔹 MAP COMPANY (SIN CAMBIOS)
    # ===============================
    def map_company(valor):

        if pd.isna(valor):
            return None

        valor = str(valor).upper()

        if "NO TRANSFER" in valor:
            return "US"
        elif "TRANSFER CO" in valor:
            return "CO"
        elif "TRANSFER EC" in valor:
            return "EC"
        elif "TRANSFER MX" in valor:
            return "MX"
        elif "TRANSFER PE" in valor:
            return "PE"
        elif "TRANSFER DR" in valor:
            return "DR"
        elif "TRANSFER BA" in valor:
            return "BA"
        elif "TRANSFER BZ" in valor:
            return "BZ"

        return None

    if "headertext" not in df.columns:
        return []

    df["company"] = df["headertext"].apply(map_company)

    # ===============================
    # 🔹 EVITAR DUPLICADOS (CLAVE)
    # ===============================
    df_unique = df.drop_duplicates(subset=[
        "product", "company", "etd", "revdelivdate"
    ])

    print("Filas originales:", len(df))
    print("Filas únicas:", len(df_unique))

    # ===============================
    # 🔹 LOOP FINAL
    # ===============================
    for _, row in df_unique.iterrows():

        producto = str(row["product"]).strip().upper()
        orderNo = str(row["orderno"]).strip().upper()
        company = row.get("company")

        owner = row.get("owner")

        if pd.isna(owner) or str(owner).strip() == "":
            owner = "SIN OWNER"
        else:
            owner = str(owner).strip().upper()

        if pd.isna(company):
            continue

        key = (company, producto)

        if key not in base_map:
            continue

        etd = row.get("etd")
        rev = row.get("revdelivdate")

        if pd.isna(etd) or pd.isna(rev):
            continue

        if etd > rev:
            continue

        leadtime_real = (rev - etd).days

        valores_base = base_map[key]

        if not valores_base:
            continue

        # ✅ USAR PRIMER VALOR COMO ANTES
        leadtime_base = valores_base[0]["valor"]

        diferencia = abs(leadtime_real - leadtime_base)

        if diferencia == 0:
            continue
        elif diferencia <= 15:
            severidad = "Media"
        elif diferencia <= 30:
            severidad = "Alta"
        else:
            severidad = "Critica"

        inconsistencias.append({
            "regla_id": regla["id"],
            "fila": int(row["_excel_row"]),
            "producto": producto,
            "orderNo": orderNo,
            "owner": owner,
            "leadtime_real": leadtime_real,
            "leadtime_base": leadtime_base,
            "detalle_base": valores_base,
            "diferencia": diferencia,
            "mensaje": f"Diferencia de LeadTime: {diferencia} días",
            "severidad": severidad
        })

    return inconsistencias



def regla_lifecycle_new_current(df, regla, bases_data):

    print("✅ Iniciando LCS_TIME")

    base_path = bases_data.get("Activations")

    if not base_path:
        print("❌ NO HAY BASE ACTIVATIONS")
        return []

    inconsistencias = []

    df_act = pd.read_excel(base_path)

    df_act.columns = (
        df_act.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    
    df_act["date_active/inactive"] = pd.to_datetime(
        df_act["date_active/inactive"], errors="coerce"
    ).dt.tz_localize(None)


    df_act = df_act[
        df_act["request"]
        .astype(str)
        .str.strip()
        .str.upper() == "ACTIVATION"
    ]

    df_act["item"] = df_act["item"].astype(str).str.strip().str.upper()

    activation_map = (
        df_act.groupby("item")["date_active/inactive"]
        .min()
        .to_dict()
    )

    col_item = None


    print("TOTAL INVENTORY:", len(df))
    print("TOTAL ACTIVATIONS:", len(activation_map))

        
    match_count = 0

    for _, row_debug in df.iterrows():
        item_debug = str(row_debug.get(col_item)).strip().upper()

        if item_debug in activation_map:
            match_count += 1

    print("TOTAL MATCH INVENTORY vs ACTIVATION:", match_count)

    for col in df.columns:
        if "item" == col:
            col_item = col
            break

    if not col_item:
        print("❌ No se encontró columna item")
        return []

    df[col_item] = df[col_item].astype(str).str.strip().str.upper()
    
    col_status = None

    for col in df.columns:
        if "status" in col:
            col_status = col
            break

    if not col_status:
        print("❌ No se encontró columna status en inventory")
        return []

    df[col_status] = df[col_status].astype(str).str.strip().str.upper()


    hoy = pd.Timestamp.now()
   

    print("TOTAL INVENTORY:", len(df))
    print("TOTAL ACTIVATIONS:", len(activation_map))

        
    inventory_path = bases_data.get("Inventario")

    owner_map = {}

    if inventory_path:
        df_inv = pd.read_excel(inventory_path)

        df_inv.columns = (
            df_inv.columns
            .astype(str)
            .str.strip()
            .str.lower()
        )

        if "item" in df_inv.columns and "owner" in df_inv.columns:
            owner_map = dict(
                zip(
                    df_inv["item"].astype(str).str.strip().str.upper(),
                    df_inv["owner"]
                )
            )
        else:
            print("⚠️ No se encontró columna item u owner en Inventory")


    for _, row in df.iterrows():

        

        item = row.get(col_item)
        status = row.get(col_status)
        wh = str(row["warehouse"]).strip().upper()
        
       
        producto = str(item).strip().upper()

        owner = str(row.get("owner", "")).strip().upper()

        if not owner:
            owner = owner_map.get(producto, "")

        if not owner:
            owner = "SIN OWNER"



        if not item or not status:
            continue

        if status not in ["NEW SELLING", "PRE-RELEASE", "CURRENT"]:
            continue

        if item not in activation_map:
            continue

        fecha = activation_map[item]

        if pd.isna(fecha):
            continue

        dias = (hoy - fecha).days

       
        if dias < 730:

            if status not in ["NEW SELLING", "PRE-RELEASE"]:
                
                inconsistencias.append({
                    "regla_id": regla["id"],
                    "fila": int(row["_excel_row"]),
                    "producto": item,
                    "owner":owner,
                    "wh": wh,
                    "status_actual": status,
                    "status_esperado": "NEW SELLING",
                    "fecha_activacion": str(fecha.date()),
                    "fecha_actual": str(hoy.date()),
                    "dias_transcurridos": dias,
                    "regla_base": 730,
                    "mensaje": f"Solo han pasado {dias} días desde la activación",
                    "severidad": regla["severidad"]
                })

        else:

            if status != "CURRENT":
                
                inconsistencias.append({
                    "regla_id": regla["id"],
                    "fila": int(row["_excel_row"]),
                    "producto": item,
                    "owner":owner,
                    "wh": wh,
                    "status_actual": status,
                    "status_esperado": "CURRENT",
                    "fecha_activacion": str(fecha.date()),
                    "fecha_actual": str(hoy.date()),
                    "dias_transcurridos": dias,
                    "regla_base": 730,
                    "mensaje": f"Han pasado {dias} días desde la activación",
                    "severidad": regla["severidad"]
                })


    return inconsistencias



def regla_datos_faltantes(df, regla):
    
        columnas = [
                col.lower().replace(" ", "").replace(".", "")
                for col in regla["columnas"]
            ]

        inconsistencias = []

        
        columnas_validas = [c for c in columnas if c in df.columns]

        if not columnas_validas:
            return inconsistencias

        for _, row in df.iterrows():

           
            producto = str(
                row.get("newcode") or row.get("product") or row.get("item") or ""
            ).strip().upper()
            owner = str(row.get("planner", "")).strip().upper() or "SIN OWNER"

         
            faltantes = []

            for col in columnas_validas:
                if pd.isna(row[col]) or str(row[col]).strip() == "":
                    faltantes.append(col)

            if faltantes:

                inconsistencias.append({
                    "regla_id": regla["id"],
                    "fila": int(row["_excel_row"]),
                    "producto": producto,
                    "owner": owner,
                    "columnas_faltantes": ", ".join(faltantes),  # 🔥 clave
                    "mensaje": "Campos obligatorios vacios:",
                    "severidad": regla["severidad"]
                })
            

        return inconsistencias
