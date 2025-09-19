import pandas as pd
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, getcontext
from django.db import transaction
from django.db.models import Q

from .models import (
    Activo, Portafolio, Precio, PesoPortafolio,
    CantidadActivo, PesoActivo, ValorPortafolio
)

getcontext().prec = 28

def to_decimal(x, default='0'):
    if pd.isna(x):
        return Decimal(default)
    s = str(x).strip()
    if s == '':
        return Decimal(default)
    # Permitir coma decimal si no hay punto
    if s.count(',') == 1 and s.count('.') == 0:
        s = s.replace(',', '.')
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return Decimal(default)

def to_date(x):
    if isinstance(x, date):
        return x
    if hasattr(x, 'date'):
        try:
            return x.date()
        except Exception:
            pass
    try:
        return pd.to_datetime(x).date()
    except Exception:
        raise ValueError(f"No se pudo convertir a fecha: {x!r}")

def cargar_datos_excel(path_xlsx, v0_value=Decimal('1000000000.00'), v0_date=None):
    try:
        xls = pd.ExcelFile(path_xlsx)
    except Exception as e:
        print(f"[ETL] No se pudo abrir {path_xlsx}: {e}")
        return False

    required = {'weights', 'Precios'}
    if not required.issubset(set(xls.sheet_names)):
        print(f"[ETL] El Excel debe tener hojas {required}. Hojas encontradas: {xls.sheet_names}")
        return False

    df_w = pd.read_excel(path_xlsx, sheet_name='weights')
    df_p = pd.read_excel(path_xlsx, sheet_name='Precios')

    if 'Dates' in df_p.columns:
        df_p = df_p.rename(columns={'Dates': 'Fecha'})

    for col in ['Fecha', 'activos', 'portafolio 1', 'portafolio 2']:
        if col not in df_w.columns:
            print(f"[ETL] Falta columna '{col}' en hoja weights")
            return False

    if 'Fecha' not in df_p.columns:
        print("[ETL] Falta columna 'Fecha' en hoja Precios")
        return False

    df_w['Fecha'] = pd.to_datetime(df_w['Fecha']).dt.date
    df_p['Fecha'] = pd.to_datetime(df_p['Fecha']).dt.date

    if v0_date is None:
        if df_w.empty:
            print("[ETL] Hoja weights vacía; no puedo inferir v0_date")
            return False
        v0_date = df_w['Fecha'].iloc[0]

    activos_w = [str(a).strip() for a in df_w['activos'].dropna().unique().tolist()]
    activos_p = [c for c in df_p.columns if c != 'Fecha']  # ancho
    activos_unicos, seen = [], set()
    for a in activos_w + activos_p:
        if a not in seen:
            activos_unicos.append(a)
            seen.add(a)

    with transaction.atomic():
        p1, _ = Portafolio.objects.get_or_create(
            nombre='Portafolio 1',
            defaults={
                'valor_inicial': v0_value,
                'fecha_inicio': v0_date,
                'descripcion': 'Primer portafolio de inversión'
            }
        )
        p2, _ = Portafolio.objects.get_or_create(
            nombre='Portafolio 2',
            defaults={
                'valor_inicial': v0_value,
                'fecha_inicio': v0_date,
                'descripcion': 'Segundo portafolio de inversión'
            }
        )
        changed = False
        if p1.valor_inicial != v0_value or p1.fecha_inicio != v0_date:
            p1.valor_inicial = v0_value; p1.fecha_inicio = v0_date; p1.save(); changed = True
        if p2.valor_inicial != v0_value or p2.fecha_inicio != v0_date:
            p2.valor_inicial = v0_value; p2.fecha_inicio = v0_date; p2.save(); changed = True
        if changed:
            print(f"[ETL] Actualizados V0/fecha_inicio de portafolios a {v0_value} / {v0_date}")

        asset_by_code = {a.codigo: a for a in Activo.objects.filter(codigo__in=activos_unicos)}
        for code in activos_unicos:
            if code not in asset_by_code:
                asset_by_code[code] = Activo.objects.create(codigo=code, nombre=code)

        precios_creados = 0
        for i, row in df_p.iterrows():
            d = row['Fecha']
            for code in activos_p:
                raw = row[code]
                if pd.isna(raw):
                    continue
                price_dec = to_decimal(raw, default=None)
                if price_dec is None:
                    print(f"[ETL] Precio inválido para {code} en {d}: {raw!r}")
                    continue
                act = asset_by_code[code]
                obj, created = Precio.objects.update_or_create(
                    activo=act, fecha=d,
                    defaults={'precio': price_dec}
                )
                if created:
                    precios_creados += 1
        print(f"[ETL] Precios upsert: {precios_creados} nuevas filas (resto actualizadas/ya existentes).")

        df_w0 = df_w[df_w['Fecha'] == v0_date].copy()
        if df_w0.empty:
            print(f"[ETL] No hay pesos en weights para {v0_date}")
            return False

        pesos_creados = 0
        for _, r in df_w0.iterrows():
            code = str(r['activos']).strip()
            w1 = to_decimal(r['portafolio 1'], default='0')
            w2 = to_decimal(r['portafolio 2'], default='0')

            act = asset_by_code.get(code)
            if not act:
                print(f"[ETL] Activo '{code}' no está en cache; se creará.")
                act, _ = Activo.objects.get_or_create(codigo=code, defaults={'nombre': code})
                asset_by_code[code] = act

            obj1, _ = PesoPortafolio.objects.update_or_create(
                portafolio=p1, activo=act,
                defaults={'peso_inicial': w1}
            )
            obj2, _ = PesoPortafolio.objects.update_or_create(
                portafolio=p2, activo=act,
                defaults={'peso_inicial': w2}
            )
            pesos_creados += 1

        print(f"[ETL] Pesos iniciales (v0) upsert: {pesos_creados} activos.")

    print("[ETL] Carga completada OK.")
    return True

def calcular_cantidades_iniciales(v0_date=date(2022, 2, 15)):
    try:
        with transaction.atomic():
            for portafolio in Portafolio.objects.all():
                print(f"[CANT] Portafolio: {portafolio.nombre}")
                for peso_portafolio in portafolio.pesos.all():
                    activo = peso_portafolio.activo
                    try:
                        p0 = Precio.objects.get(activo=activo, fecha=v0_date).precio
                    except Precio.DoesNotExist:
                        print(f"[CANT] Sin precio v0 para {activo.codigo} en {v0_date}")
                        continue
                    if p0 is None or p0 == 0:
                        print(f"[CANT] Precio cero/nulo para {activo.codigo} en {v0_date}")
                        continue

                    c0 = (peso_portafolio.peso_inicial * portafolio.valor_inicial) / p0
                    CantidadActivo.objects.update_or_create(
                        portafolio=portafolio,
                        activo=activo,
                        fecha=v0_date,
                        defaults={'cantidad': c0}
                    )
                    print(f"[CANT] {activo.codigo}: c0={c0}")
        print("[CANT] Cantidades iniciales listas.")
        return True
    except Exception as e:
        print(f"[CANT] Error: {e}")
        import traceback; traceback.print_exc()
        return False

def calcular_valores_historicos():
    try:
        with transaction.atomic():
            fechas = list(Precio.objects.values_list('fecha', flat=True).distinct().order_by('fecha'))
            if not fechas:
                print("[VAL] No hay precios cargados.")
                return False
            for f in fechas:
                print(f"[VAL] Fecha: {f}")
                for pf in Portafolio.objects.all():
                    Vt = Decimal('0')
                    for peso_pf in pf.pesos.select_related('activo').all():
                        a = peso_pf.activo
                        try:
                            p_it = Precio.objects.get(activo=a, fecha=f).precio
                        except Precio.DoesNotExist:
                            continue
                        c_obj = CantidadActivo.objects.filter(
                            portafolio=pf, activo=a, fecha__lte=f
                        ).order_by('-fecha').first()
                        if not c_obj:
                            continue
                        c_it = c_obj.cantidad

                        x_it = c_it * p_it
                        Vt += x_it

                        PesoActivo.objects.update_or_create(
                            portafolio=pf, activo=a, fecha=f,
                            defaults={'valor_activo': x_it, 'peso': Decimal('0')}
                        )

                    if Vt > 0:
                        ValorPortafolio.objects.update_or_create(
                            portafolio=pf, fecha=f,
                            defaults={'valor_total': Vt}
                        )
                        for pa in PesoActivo.objects.filter(portafolio=pf, fecha=f):
                            pa.peso = (pa.valor_activo / Vt) if Vt else Decimal('0')
                            pa.save()
            print("[VAL] Series históricas recalculadas.")
            return True
    except Exception as e:
        print(f"[VAL] Error: {e}")
        import traceback; traceback.print_exc()
        return False
