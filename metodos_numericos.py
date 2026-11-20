"""
RaízLab - Métodos numéricos: Bisección y Bairstow (consola).

Ejecutar:   python metodos_numericos.py
Gráficas:   graficas.py (necesita matplotlib:  pip install matplotlib)
Pruebas:    python pruebas.py

Estructura (RNF-07):
  - biseccion() y bairstow(): solo cálculo; devuelven resultados e historial.
  - explicar_biseccion() y explicar_bairstow(): muestran el paso a paso.
  - main(): menú interactivo, validaciones y exportación CSV.
"""
import ast
import cmath
import csv
import math
import operator

MAX_ITER_LIMITE = 500

# ---------------------------------------------------------------------------
# Evaluador seguro de expresiones (RNF-05): nada se ejecuta como código.
# ---------------------------------------------------------------------------
_FUNCIONES = {"sin": math.sin, "cos": math.cos, "tan": math.tan, "exp": math.exp,
              "log": math.log, "ln": math.log, "sqrt": math.sqrt, "abs": abs,
              "asin": math.asin, "acos": math.acos, "atan": math.atan}
_CONSTANTES = {"PI": math.pi, "E": math.e, "pi": math.pi, "e": math.e}
_BINARIOS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
             ast.Div: operator.truediv, ast.Pow: operator.pow}
_UNARIOS = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def crear_funcion(expr):
    """Convierte un texto como 'x^3 - x - 2' en una función f(x) de forma segura."""
    if not expr or not expr.strip():
        raise ValueError("Ingresa la función f(x).")
    try:
        arbol = ast.parse(expr.replace("^", "**").strip(), mode="eval")
    except SyntaxError:
        raise ValueError("Error: la expresión no es válida (revisa paréntesis y operadores).")

    def ev(nodo, x):
        if isinstance(nodo, ast.Expression):
            return ev(nodo.body, x)
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)) \
                and not isinstance(nodo.value, bool):
            return float(nodo.value)
        if isinstance(nodo, ast.Name):
            if nodo.id == "x":
                return x
            if nodo.id in _CONSTANTES:
                return _CONSTANTES[nodo.id]
        if isinstance(nodo, ast.BinOp) and type(nodo.op) in _BINARIOS:
            return _BINARIOS[type(nodo.op)](ev(nodo.left, x), ev(nodo.right, x))
        if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _UNARIOS:
            return _UNARIOS[type(nodo.op)](ev(nodo.operand, x))
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) \
                and nodo.func.id in _FUNCIONES and len(nodo.args) == 1 and not nodo.keywords:
            return _FUNCIONES[nodo.func.id](ev(nodo.args[0], x))
        raise ValueError("Error: la expresión no es válida. Solo se permiten números, "
                         "x, + - * / ^, sin, cos, tan, exp, log, ln, sqrt, abs, PI y E.")

    def f(x):
        try:
            valor = float(ev(arbol, x))
            if not math.isfinite(valor):
                raise ValueError("La función produjo un valor no finito.")
            return valor
        except (ZeroDivisionError, OverflowError):
            raise ValueError("Error: la función no se puede evaluar en x = %g." % x)
        except TypeError:
            raise ValueError("Error: la expresión no es válida.")
    # Validar la sintaxis sin asumir que x=1 pertenece al dominio.
    if len(expr) > 300 or len(list(ast.walk(arbol))) > 100:
        raise ValueError("La expresión es demasiado larga.")
    def validar(n):
        if isinstance(n, ast.Expression): return validar(n.body)
        if isinstance(n, ast.Constant) and type(n.value) in (int, float): return
        if isinstance(n, ast.Name) and n.id in {"x", *_CONSTANTES}: return
        if isinstance(n, ast.BinOp) and type(n.op) in _BINARIOS:
            validar(n.left); validar(n.right); return
        if isinstance(n, ast.UnaryOp) and type(n.op) in _UNARIOS:
            validar(n.operand); return
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCIONES and len(n.args)==1 and not n.keywords:
            validar(n.args[0]); return
        raise ValueError("Expresión no permitida. Usa números, x y funciones matemáticas.")
    validar(arbol)
    return f


def texto_polinomio(coef):
    """coef en orden descendente: [a_n, ..., a_0]."""
    n = len(coef) - 1
    s = ""
    for i, c in enumerate(coef):
        g = n - i
        if c == 0:
            continue
        t = "" if (abs(c) == 1 and g > 0) else f"{abs(c):g}"
        t += f"x^{g}" if g > 1 else ("x" if g == 1 else "")
        if not s:
            s = ("-" if c < 0 else "") + t
        else:
            s += (" - " if c < 0 else " + ") + t
    return s or "0"


def _error_pct(delta, nuevo):
    """Error porcentual |Δ/nuevo|·100. Si el valor nuevo tiende a 0 se usa |Δ|·100
    para que el criterio no quede indefinido (RNF-04)."""
    if abs(nuevo) < 1e-9:
        return abs(delta) * 100
    return abs(delta / nuevo) * 100


# ---------------------------------------------------------------------------
# Bisección: cálculo
# ---------------------------------------------------------------------------
def biseccion(f, a, b, tol=0.01, max_iter=50):
    """Devuelve un diccionario con raíz, historial completo y si convergió."""
    if not a < b:
        raise ValueError("Se necesita a < b.")
    fa0, fb0 = f(a), f(b)
    res = dict(a0=a, b0=b, fa0=fa0, fb0=fb0, tol=tol, max_iter=max_iter,
               historial=[], convergio=False, raiz=None, fraiz=None, ea=None)
    if fa0 == 0 or fb0 == 0:
        res.update(sin_cambio=False, convergio=True, raiz=a if fa0 == 0 else b,
                   fraiz=0.0, ea=0.0)
        return res
    if (fa0 > 0) == (fb0 > 0):
        res["sin_cambio"] = True
        return res
    res["sin_cambio"] = False
    c_ant, c = None, a
    for i in range(1, max_iter + 1):
        c = (a + b) / 2
        fa, fb, fc = f(a), f(b), f(c)
        prod = fa * fc
        ea = None if c_ant is None else _error_pct(c - c_ant, c)
        if fc != 0 and (fa > 0) != (fc > 0):
            decision, a_n, b_n = "f(a)·f(c) < 0: la raíz está en [a, c]  →  b = c", a, c
        elif fc != 0:
            decision, a_n, b_n = "f(a)·f(c) > 0: la raíz está en [c, b]  →  a = c", c, b
        else:
            decision, a_n, b_n = "f(c) = 0: c es raíz exacta", a, b
        res["historial"].append(dict(i=i, a=a, b=b, c=c, fa=fa, fb=fb, fc=fc, prod=prod,
                                     ea=ea, decision=decision, a_nuevo=a_n, b_nuevo=b_n))
        res["ea"] = ea
        if fc == 0 or (ea is not None and ea < tol):
            res["convergio"] = True
            break
        a, b, c_ant = a_n, b_n, c
    res["raiz"], res["fraiz"] = c, f(c)
    return res


def explicar_biseccion(res, expr=""):
    """Paso a paso de la bisección (RF-05, RF-06, RF-08, RF-10, RF-11)."""
    a, b = res["a0"], res["b0"]
    print("\n" + "=" * 70)
    print(f"MÉTODO DE BISECCIÓN   f(x) = {expr}")
    print("=" * 70)
    print("\nPASO 1. Verificar el intervalo (teorema de Bolzano)")
    print(f"  f({a:g}) = {res['fa0']:.6f}")
    print(f"  f({b:g}) = {res['fb0']:.6f}")
    print(f"  f(a)·f(b) = {res['fa0'] * res['fb0']:.6f}")
    if res["sin_cambio"]:
        print("  No hay cambio de signo: elige otro intervalo [a, b].")
        return
    print("  Hay cambio de signo: existe al menos una raíz en [a, b].")
    print("\nPASO 2. Fórmulas")
    print("  c = (a + b) / 2")
    print("  Si f(a)·f(c) < 0 → b = c;  si f(a)·f(c) > 0 → a = c;  si = 0 → c es la raíz")
    print("  εa = |(c_actual − c_anterior) / c_actual| · 100")
    print(f"\nPASO 3. Criterio de parada: εa < {res['tol']:g} %  "
          f"(máximo {res['max_iter']} iteraciones)")
    print("\nPASO 4. Iteraciones, una por una")
    for h in res["historial"]:
        print(f"\n--- Iteración {h['i']} ---")
        print(f"  Intervalo actual: [{h['a']:.6f}, {h['b']:.6f}]")
        print(f"  c = (a + b)/2 = ({h['a']:.6f} + {h['b']:.6f})/2 = {h['c']:.6f}")
        print(f"  f(a) = {h['fa']:.6f}      f(c) = {h['fc']:.6f}")
        print(f"  f(a)·f(c) = {h['fa']:.6f} · {h['fc']:.6f} = {h['prod']:.6f}")
        print(f"  Decisión: {h['decision']}")
        print(f"  Nuevo intervalo: [{h['a_nuevo']:.6f}, {h['b_nuevo']:.6f}]")
        if h["ea"] is None:
            print("  εa = — (primera iteración, no hay c anterior)")
        else:
            ant = res["historial"][h["i"] - 2]["c"]
            print(f"  εa = |({h['c']:.6f} − {ant:.6f}) / {h['c']:.6f}| · 100 = {h['ea']:.4f} %"
                  f"   ({'<' if h['ea'] < res['tol'] else '≥'} {res['tol']:g} %)")
    print("\nTABLA RESUMEN")
    print(f"{'i':>3} {'a':>11} {'b':>11} {'c':>11} {'f(a)':>11} {'f(c)':>11} "
          f"{'f(a)f(c)':>11} {'Ea %':>9}")
    for h in res["historial"]:
        ea = "—" if h["ea"] is None else f"{h['ea']:.4f}"
        print(f"{h['i']:>3} {h['a']:>11.6f} {h['b']:>11.6f} {h['c']:>11.6f} {h['fa']:>11.6f} "
              f"{h['fc']:>11.6f} {h['prod']:>11.6f} {ea:>9}")
    print("\nRESUMEN")
    print(f"  Raíz aproximada : {res['raiz']:.6f}")
    print(f"  f(raíz)         : {res['fraiz']:.6f}")
    print(f"  Iteraciones     : {len(res['historial'])}")
    ea_txt = "—" if res["ea"] is None else f"{res['ea']:.4f} %"
    print(f"  εa final        : {ea_txt}")
    print(f"  Tolerancia      : {res['tol']:g} %")
    if res["convergio"]:
        print("  ¿Se alcanzó la tolerancia? Sí")
    else:
        print("  ¿Se alcanzó la tolerancia? No: se llegó al límite de iteraciones "
              "sin cumplir la tolerancia.")


# ---------------------------------------------------------------------------
# Bairstow: cálculo
# ---------------------------------------------------------------------------
def _vector_b(a, r, s):
    n = len(a) - 1
    b = [0.0] * (n + 1)
    b[n] = a[n]
    b[n - 1] = a[n - 1] + r * b[n]
    for k in range(n - 2, -1, -1):
        b[k] = a[k] + r * b[k + 1] + s * b[k + 2]
    return b


def _vector_c(b, r, s):
    n = len(b) - 1
    c = [0.0] * (n + 1)
    c[n] = b[n]
    c[n - 1] = b[n - 1] + r * c[n]
    for k in range(n - 2, 0, -1):
        c[k] = b[k] + r * c[k + 1] + s * c[k + 2]
    return c


def _raices_cuadratico(r, s):
    """Raíces de x² − r·x − s = 0."""
    d = cmath.sqrt(r * r + 4 * s)
    return [(r + d) / 2, (r - d) / 2]


def _limpia(z):
    return complex(z.real, 0.0) if abs(z.imag) < 1e-12 else z


def bairstow(coef, r0=-1.0, s0=-1.0, tol=0.01, max_iter=50):
    """coef de MAYOR a MENOR grado. Devuelve raíces e historial por factor."""
    a = list(reversed([float(x) for x in coef]))
    res = dict(coef=list(coef), r0=r0, s0=s0, tol=tol, max_iter=max_iter,
               factores=[], final=None, raices=[], convergio=True)
    while len(a) - 1 >= 3:
        n = len(a) - 1
        r, s = r0, s0
        fac = dict(grado=n, a=list(a), iteraciones=[], convergio=False)
        for it in range(1, max_iter + 1):
            b = _vector_b(a, r, s)
            c = _vector_c(b, r, s)
            det = c[2] * c[2] - c[3] * c[1]
            if abs(det) < 1e-14:
                raise ZeroDivisionError("El determinante es 0. Prueba otros valores "
                                        "iniciales de r y s.")
            dr = (-b[1] * c[2] + c[3] * b[0]) / det
            ds = (-b[0] * c[2] + c[1] * b[1]) / det
            rn, sn = r + dr, s + ds
            if not all(math.isfinite(v) for v in (rn, sn, dr, ds, det)):
                raise ValueError("Bairstow produjo valores no finitos. Cambia r y s.")
            er, es = _error_pct(dr, rn), _error_pct(ds, sn)
            fac["iteraciones"].append(dict(it=it, r=r, s=s, b=b, c=c, det=det, dr=dr,
                                           ds=ds, r_nuevo=rn, s_nuevo=sn, er=er, es=es))
            r, s = rn, sn
            if er < tol and es < tol:
                fac["convergio"] = True
                break
        if not fac["convergio"]:
            res["convergio"] = False
            fac.update(r=r, s=s, raices=[], b_final=_vector_b(a, r, s), deflactado=[])
            res["factores"].append(fac)
            return res  # No extraer raíces ni deflactar un factor no convergente.
        fac["r"], fac["s"] = r, s
        fac["raices"] = [_limpia(z) for z in _raices_cuadratico(r, s)]
        b = _vector_b(a, r, s)
        fac["b_final"] = b
        a = b[2:]
        fac["deflactado"] = list(reversed(a))
        res["raices"].extend(fac["raices"])
        res["factores"].append(fac)
    n = len(a) - 1
    if n == 2:
        d = cmath.sqrt(a[1] ** 2 - 4 * a[2] * a[0])
        nuevas = [(-a[1] + d) / (2 * a[2]), (-a[1] - d) / (2 * a[2])]
        res["final"] = dict(grado=2, a=list(a), raices=[_limpia(z) for z in nuevas])
    elif n == 1:
        res["final"] = dict(grado=1, a=list(a), raices=[complex(-a[0] / a[1], 0)])
    if res["final"]:
        res["raices"].extend(res["final"]["raices"])
    return res


def _fz(z):
    z = complex(z)
    if abs(z.imag) < 1e-12:
        return f"{z.real:.6f}"
    return f"{z.real:.6f} {'+' if z.imag >= 0 else '−'} {abs(z.imag):.6f}i"


def explicar_bairstow(res):
    """Paso a paso de Bairstow (RF-07, RF-08, RF-10, RF-11)."""
    coef = res["coef"]
    print("\n" + "=" * 70)
    print(f"MÉTODO DE BAIRSTOW   P(x) = {texto_polinomio(coef)}")
    print("=" * 70)
    print("\nPASO 1. Idea del método")
    print("  Se busca un factor cuadrático  x² − r·x − s  que divida al polinomio.")
    print(f"  Valores iniciales: r = {res['r0']:g}, s = {res['s0']:g};  "
          f"tolerancia {res['tol']:g} %, máximo {res['max_iter']} iteraciones por factor.")
    print("\nPASO 2. Fórmulas")
    print("  b_n = a_n ;  b_(n-1) = a_(n-1) + r·b_n ;  b_k = a_k + r·b_(k+1) + s·b_(k+2)")
    print("  c_n = b_n ;  c_(n-1) = b_(n-1) + r·c_n ;  c_k = b_k + r·c_(k+1) + s·c_(k+2)")
    print("  Sistema:  c2·Δr + c3·Δs = −b1   y   c1·Δr + c2·Δs = −b0")
    print("  Cramer:   det = c2² − c3·c1 ;  Δr = (−b1·c2 + c3·b0)/det ;  "
          "Δs = (−b0·c2 + c1·b1)/det")
    print("  r_nuevo = r + Δr ;  s_nuevo = s + Δs ;  εr = |Δr/r_nuevo|·100 ;  "
          "εs = |Δs/s_nuevo|·100")
    print("  Raíces del factor:  x = (r ± √(r² + 4s)) / 2")
    for k, fac in enumerate(res["factores"], 1):
        print(f"\n{'#' * 70}\nFACTOR {k}  (polinomio actual de grado {fac['grado']}: "
              f"{texto_polinomio(list(reversed(fac['a'])))})\n{'#' * 70}")
        a = fac["a"]
        n = fac["grado"]
        for h in fac["iteraciones"]:
            r, s, b, c = h["r"], h["s"], h["b"], h["c"]
            print(f"\n--- Factor {k}, iteración {h['it']} ---")
            print(f"  r = {r:.6f}   s = {s:.6f}")
            print("  Vector b (división sintética):")
            print(f"    b{n} = a{n} = {b[n]:.6f}")
            print(f"    b{n-1} = a{n-1} + r·b{n} = {a[n-1]:.6f} + ({r:.6f})({b[n]:.6f}) "
                  f"= {b[n-1]:.6f}")
            for j in range(n - 2, -1, -1):
                print(f"    b{j} = a{j} + r·b{j+1} + s·b{j+2} = {a[j]:.6f} + ({r:.6f})"
                      f"({b[j+1]:.6f}) + ({s:.6f})({b[j+2]:.6f}) = {b[j]:.6f}")
            print("  Vector c:")
            print(f"    c{n} = b{n} = {c[n]:.6f}")
            print(f"    c{n-1} = b{n-1} + r·c{n} = {b[n-1]:.6f} + ({r:.6f})({c[n]:.6f}) "
                  f"= {c[n-1]:.6f}")
            for j in range(n - 2, 0, -1):
                print(f"    c{j} = b{j} + r·c{j+1} + s·c{j+2} = {b[j]:.6f} + ({r:.6f})"
                      f"({c[j+1]:.6f}) + ({s:.6f})({c[j+2]:.6f}) = {c[j]:.6f}")
            print("  Sistema de ecuaciones:")
            print(f"    ({c[2]:.6f})Δr + ({c[3]:.6f})Δs = {-b[1]:.6f}")
            print(f"    ({c[1]:.6f})Δr + ({c[2]:.6f})Δs = {-b[0]:.6f}")
            print(f"  det = ({c[2]:.6f})² − ({c[3]:.6f})({c[1]:.6f}) = {h['det']:.6f}")
            print(f"  Δr = {h['dr']:.6f}      Δs = {h['ds']:.6f}")
            print(f"  r_nuevo = {r:.6f} + ({h['dr']:.6f}) = {h['r_nuevo']:.6f}")
            print(f"  s_nuevo = {s:.6f} + ({h['ds']:.6f}) = {h['s_nuevo']:.6f}")
            ok = h["er"] < res["tol"] and h["es"] < res["tol"]
            veredicto = ("ambos < %g %%: converge" % res["tol"]) if ok else "aún no converge"
            print(f"  εr = {h['er']:.4f} %    εs = {h['es']:.4f} %   →  {veredicto}")
        if not fac["convergio"]:
            print("  Aviso: No alcanzó la tolerancia en el máximo de iteraciones.")
        if not fac['convergio']:
            print("  No se extraen raíces de este factor ni se continúa la deflación.")
            return
        print(f"\n  Factor encontrado: x² − ({fac['r']:.6f})x − ({fac['s']:.6f})")
        print(f"  Raíces (r ± √(r²+4s))/2: {_fz(fac['raices'][0])} ; {_fz(fac['raices'][1])}")
        print(f"  Deflación: el cociente son b{n}…b2 → "
              f"{texto_polinomio(fac['deflactado'])}")
    fin = res["final"]
    if fin:
        print(f"\n{'#' * 70}\nPOLINOMIO RESTANTE (grado {fin['grado']}): "
              f"{texto_polinomio(list(reversed(fin['a'])))}\n{'#' * 70}")
        if fin["grado"] == 2:
            a0, a1, a2 = fin["a"]
            print(f"  Fórmula general: x = (−a1 ± √(a1² − 4·a2·a0)) / (2·a2) con "
                  f"a2 = {a2:.6f}, a1 = {a1:.6f}, a0 = {a0:.6f}")
        else:
            a0, a1 = fin["a"]
            print(f"  x = −a0/a1 = −({a0:.6f})/({a1:.6f})")
        print("  Raíces: " + " ; ".join(_fz(z) for z in fin["raices"]))
    print("\nRESUMEN")
    for k, z in enumerate(res["raices"], 1):
        print(f"  x{k} = {_fz(z)}")
    print(f"  Factores cuadráticos: {len(res['factores'])} "
          f"(iteraciones: {', '.join(str(len(f['iteraciones'])) for f in res['factores']) or '—'})")
    print(f"  Tolerancia: {res['tol']:g} %")
    print("  ¿Se alcanzó la tolerancia en todos los factores? "
          + ("Sí" if res["convergio"] else "No"))


# ---------------------------------------------------------------------------
# Exportar CSV (RF-12)
# ---------------------------------------------------------------------------
def exportar_csv(res, metodo, ruta):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        if metodo == "biseccion":
            w.writerow(["RESUMEN"])
            w.writerow(["raiz", res["raiz"]]); w.writerow(["f(raiz)", res["fraiz"]])
            w.writerow(["iteraciones", len(res["historial"])])
            w.writerow(["tolerancia_%", res["tol"]])
            w.writerow(["alcanzo_tolerancia", "Sí" if res["convergio"] else "No"])
            w.writerow([])
            w.writerow(["i", "a", "b", "c", "f(a)", "f(c)", "f(a)f(c)", "Ea_%"])
            for h in res["historial"]:
                w.writerow([h["i"], h["a"], h["b"], h["c"], h["fa"], h["fc"], h["prod"],
                            "" if h["ea"] is None else h["ea"]])
        else:
            w.writerow(["RESUMEN"])
            for k, z in enumerate(res["raices"], 1):
                w.writerow([f"x{k}", z.real, z.imag])
            w.writerow(["tolerancia_%", res["tol"]])
            w.writerow(["alcanzo_tolerancia", "Sí" if res["convergio"] else "No"])
            w.writerow([])
            w.writerow(["factor", "it", "r", "s", "b1", "b0", "dr", "ds", "er_%", "es_%"])
            for k, fac in enumerate(res["factores"], 1):
                for h in fac["iteraciones"]:
                    w.writerow([k, h["it"], h["r"], h["s"], h["b"][1], h["b"][0],
                                h["dr"], h["ds"], h["er"], h["es"]])


# ---------------------------------------------------------------------------
# Validación de entradas (RF-04) y menú (RF-01, RF-03, RF-13)
# ---------------------------------------------------------------------------
def _num(txt, nombre):
    try:
        return float(txt.strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"{nombre} debe ser un número.")


def _parametros_comunes(tol_txt, it_txt):
    tol = _num(tol_txt, "La tolerancia")
    if tol <= 0:
        raise ValueError("La tolerancia debe ser mayor que 0.")
    try:
        it = int(it_txt.strip())
    except ValueError:
        raise ValueError("Las iteraciones máximas deben ser un número entero.")
    if not 1 <= it <= MAX_ITER_LIMITE:
        raise ValueError(f"Las iteraciones máximas deben estar entre 1 y {MAX_ITER_LIMITE}.")
    return tol, it


def _pedir(msg, defecto):
    t = input(f"{msg} [{defecto}]: ").strip()
    return t if t else str(defecto)


def pedir_biseccion():
    expr = _pedir("f(x) (use ^ para potencias; sin, cos, exp, log, sqrt, PI, E)", "x^3 - x - 2")
    f = crear_funcion(expr)
    a = _num(_pedir("a", 1), "a")
    b = _num(_pedir("b", 2), "b")
    tol, it = _parametros_comunes(_pedir("Tolerancia (%)", 0.01),
                                  _pedir("Iteraciones máximas (1-500)", 50))
    return dict(metodo="biseccion", expr=expr, f=f, a=a, b=b, tol=tol, it=it)


def pedir_bairstow():
    txt = _pedir("Coeficientes de mayor a menor grado, separados por coma",
                 "1, -3.5, 2.75, 2.125, -3.875, 1.25")
    try:
        coef = [float(x) for x in txt.split(",")]
    except ValueError:
        raise ValueError("Ingresa al menos 3 coeficientes numéricos.")
    if len(coef) < 3:
        raise ValueError("Ingresa al menos 3 coeficientes numéricos.")
    if coef[0] == 0:
        raise ValueError("El primer coeficiente no puede ser 0.")
    r0 = _num(_pedir("r inicial", -1), "r")
    s0 = _num(_pedir("s inicial", -1), "s")
    tol, it = _parametros_comunes(_pedir("Tolerancia (%)", 0.01),
                                  _pedir("Iteraciones máximas (1-500)", 50))
    return dict(metodo="bairstow", coef=coef, r0=r0, s0=s0, tol=tol, it=it)


def ejecutar(datos, mostrar_graficas=True):
    """Calcula, explica paso a paso y (opcional) abre las gráficas."""
    if datos["metodo"] == "biseccion":
        res = biseccion(datos["f"], datos["a"], datos["b"], datos["tol"], datos["it"])
        explicar_biseccion(res, datos["expr"])
        if res["sin_cambio"] or not mostrar_graficas:
            return res
        try:
            import graficas
            graficas.graficar_biseccion(res, datos["f"], datos["expr"])
        except ImportError:
            print("\n(Para ver las gráficas instala matplotlib: pip install matplotlib)")
        return res
    res = bairstow(datos["coef"], datos["r0"], datos["s0"], datos["tol"], datos["it"])
    explicar_bairstow(res)
    if mostrar_graficas:
        try:
            import graficas
            graficas.graficar_bairstow(res)
        except ImportError:
            print("\n(Para ver las gráficas instala matplotlib: pip install matplotlib)")
    return res


def main():
    ultimo = ultimo_res = None
    while True:
        print("\n===== RaízLab =====")
        print("1) Bisección   2) Bairstow   3) Repetir cálculo   "
              "4) Exportar CSV   5) Limpiar   0) Salir")
        op = input("Elige una opción: ").strip()
        try:
            if op == "1":
                ultimo = pedir_biseccion()
                ultimo_res = ejecutar(ultimo)
            elif op == "2":
                ultimo = pedir_bairstow()
                ultimo_res = ejecutar(ultimo)
            elif op == "3":
                if not ultimo:
                    print("Aún no hay un cálculo para repetir.")
                else:
                    ultimo_res = ejecutar(ultimo)
            elif op == "4":
                if not ultimo_res or ultimo_res.get("sin_cambio"):
                    print("No hay resultados para exportar.")
                else:
                    ruta = input("Nombre del archivo [resultados.csv]: ").strip() or "resultados.csv"
                    exportar_csv(ultimo_res, ultimo["metodo"], ruta)
                    print(f"Archivo guardado: {ruta}")
            elif op == "5":
                ultimo = ultimo_res = None
                print("Formulario limpio. Elige un método para un ejercicio nuevo.")
            elif op == "0":
                break
            else:
                print("Opción no válida.")
        except (ValueError, ZeroDivisionError) as e:
            print(f"\n{e}")


if __name__ == "__main__":
    main()
