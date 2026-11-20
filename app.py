"""Interfaz web local de RaízLab. Ejecutar: python app.py."""
import csv
import io
import math
import re
from polinomios import extraer_coeficientes
from flask import Flask, render_template, request, Response, jsonify
from metodos_numericos import crear_funcion, biseccion, bairstow, texto_polinomio, _fz

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
DEFAULTS = dict(metodo='biseccion', expr='x^3 - x - 2', a='1', b='2',
                coef='x^3 - 6x^2 + 11x - 6', r='-1', s='-1', tol='0.01', it='100')


def numero(d, key):
    v = float(d[key].replace(',', '.'))
    if not math.isfinite(v) or abs(v) > 1e12:
        raise ValueError('Usa números finitos con magnitud no mayor de 10^12.')
    return v


@app.template_filter('lineas_proceso')
def lineas_proceso(texto):
    # Divide operaciones y frases, sin cortar los puntos decimales.
    return [linea.strip() for linea in re.split(r';\s*|(?<=[.])\s+(?=[A-ZÁÉÍÓÚ¿])', texto) if linea.strip()]

@app.template_filter('titulo_paso')
def titulo_paso(texto):
    return re.sub(r'^\d+\.\s*', '', texto)


def desarrollo(res, metodo, expr=""):
    """Explicaciones con sustitución numérica; una tarjeta por iteración."""
    fmt = lambda v: f"{v:.8g}"
    pasos = []
    sustituir = lambda x: re.sub(r'\bx\b', '('+fmt(x)+')', expr)
    if metodo == 'biseccion':
        for j, h in enumerate(res['historial']):
            anterior = res['historial'][j-1]['c'] if j else None
            error = 'No se calcula: todavía no hay una aproximación anterior.'
            if anterior is not None:
                delta = h['c']-anterior
                error = (f"Ea = |{fmt(delta)}| × 100 = {fmt(h['ea'])} % (criterio alternativo cerca de cero)."
                         if abs(h['c']) < 1e-9 else
                         f"Ea = |({fmt(h['c'])} − ({fmt(anterior)})) / {fmt(h['c'])}| × 100 = {fmt(h['ea'])} %.")
            estado = ('Raíz exacta: f(c) = 0.' if h['fc']==0 else
                      'Tolerancia alcanzada.' if h['ea'] is not None and h['ea']<res['tol'] else
                      'Se alcanzó el límite sin cumplir la tolerancia.' if j==len(res['historial'])-1 else
                      'Aún no cumple la tolerancia; se continúa.')
            pasos.append(dict(titulo=f"Iteración {h['i']}", bloques=[
                ['1. Punto medio',f"c = (a + b) / 2 = ({fmt(h['a'])} + {fmt(h['b'])}) / 2 = {fmt(h['c'])}"],
                ['2. Evaluación',f"f(a) = {sustituir(h['a'])} = {fmt(h['fa'])}; f(c) = {sustituir(h['c'])} = {fmt(h['fc'])}; f(a) × f(c) = ({fmt(h['fa'])}) × ({fmt(h['fc'])}) = {fmt(h['prod'])}"],
                ['3. Nuevo intervalo',h['decision']+f". Intervalo: [{fmt(h['a_nuevo'])}, {fmt(h['b_nuevo'])}]"],
                ['4. Error y parada',error+f" Tolerancia: {fmt(res['tol'])} %. "+estado]], extras=[]))
    else:
        for k, fac in enumerate(res['factores'],1):
            for j,h in enumerate(fac['iteraciones']):
                b,c=h['b'],h['c']; n=fac['grado']; a=fac['a']; r=h['r']; ss=h['s']
                extras=[f"b{n} = a{n} = {fmt(b[n])}",f"b{n-1} = {fmt(a[n-1])} + ({fmt(r)}) × ({fmt(b[n])}) = {fmt(b[n-1])}"]
                extras += [f"b{t} = {fmt(a[t])} + ({fmt(r)}) × ({fmt(b[t+1])}) + ({fmt(ss)}) × ({fmt(b[t+2])}) = {fmt(b[t])}" for t in range(n-2,-1,-1)]
                extras += [f"c{n} = b{n} = {fmt(c[n])}", f"c{n-1} = {fmt(b[n-1])} + ({fmt(r)}) × ({fmt(c[n])}) = {fmt(c[n-1])}"]
                extras += [f"c{t} = {fmt(b[t])} + ({fmt(r)}) × ({fmt(c[t+1])}) + ({fmt(ss)}) × ({fmt(c[t+2])}) = {fmt(c[t])}" for t in range(n-2,0,-1)]
                er = (f"|{fmt(h['dr'])}| × 100" if abs(h['r_nuevo'])<1e-9 else f"|{fmt(h['dr'])} / {fmt(h['r_nuevo'])}| × 100")
                es = (f"|{fmt(h['ds'])}| × 100" if abs(h['s_nuevo'])<1e-9 else f"|{fmt(h['ds'])} / {fmt(h['s_nuevo'])}| × 100")
                ok=h['er']<res['tol'] and h['es']<res['tol']
                cierre = ('Ambos errores cumplen: se extraen las raíces del factor.' if ok else
                          'Límite alcanzado: este factor no se extrae.' if j==len(fac['iteraciones'])-1 else 'Se continúa con los nuevos r y s.')
                bloques=[['1. División sintética',f"r = {fmt(r)}; s = {fmt(ss)}. Residuos: b1 = {fmt(b[1])}; b0 = {fmt(b[0])}. A continuación se desarrollan los vectores b y c."],
                    ['2. Sistema y determinante',f"({fmt(c[2])})Δr + ({fmt(c[3])})Δs = {fmt(-b[1])}; ({fmt(c[1])})Δr + ({fmt(c[2])})Δs = {fmt(-b[0])}. det = ({fmt(c[2])})² − ({fmt(c[3])})({fmt(c[1])}) = {fmt(h['det'])}"],
                    ['3. Correcciones',f"Δr = (−({fmt(b[1])})({fmt(c[2])}) + ({fmt(c[3])})({fmt(b[0])})) / ({fmt(h['det'])}) = {fmt(h['dr'])}. Δs = (−({fmt(b[0])})({fmt(c[2])}) + ({fmt(c[1])})({fmt(b[1])})) / ({fmt(h['det'])}) = {fmt(h['ds'])}."],
                    ['4. Actualización',f"r nuevo = {fmt(r)} + ({fmt(h['dr'])}) = {fmt(h['r_nuevo'])}; s nuevo = {fmt(ss)} + ({fmt(h['ds'])}) = {fmt(h['s_nuevo'])}"],
                    ['5. Error y parada',f"Er = {er} = {fmt(h['er'])} %; Es = {es} = {fmt(h['es'])} %. Tolerancia: {fmt(res['tol'])} %. "+cierre]]
                if ok:
                    bloques.append(['6. Raíces y deflación',f"x = ({fmt(fac['r'])} ± √(({fmt(fac['r'])})² + 4({fmt(fac['s'])}))) / 2. Raíces: {', '.join(_fz(z) for z in fac['raices'])}. Cociente: {texto_polinomio(fac['deflactado'])}."])
                pasos.append(dict(titulo=f"Factor {k} · Iteración {h['it']}",bloques=bloques,extras=extras))
    return pasos


def calcular(d):
    tol, it = numero(d, 'tol'), int(d['it'])
    if tol <= 0 or it < 1:
        raise ValueError('La tolerancia debe ser positiva y el máximo de iteraciones un entero positivo.')
    if d['metodo'] == 'biseccion':
        f = crear_funcion(d['expr'])
        a, b = numero(d, 'a'), numero(d, 'b')
        res = biseccion(f, a, b, tol, it)
        if res['sin_cambio']:
            raise ValueError('No hay cambio de signo. Prueba otro intervalo; esto no significa que la función no tenga raíces.')
        rows = [[h[k] for k in ('i','a','b','c','fc','ea','decision')] for h in res['historial']]
        headers = ['Iteración','a','b','c','f(c)','Error %','Decisión']
        roots = [str(res['raiz'])]
        title = 'f(x) = ' + d['expr']
        residuals = [abs(res['fraiz'])]
    elif d['metodo'] == 'bairstow':
        coef = extraer_coeficientes(d['coef'])
        res = bairstow(coef, numero(d,'r'), numero(d,'s'), tol, it)
        rows = [[k,h['it'],h['r_nuevo'],h['s_nuevo'],h['dr'],h['ds'],h['er'],h['es']] for k,fac in enumerate(res['factores'],1) for h in fac['iteraciones']]
        headers = ['Factor','Iteración','r nuevo','s nuevo','Δr','Δs','Error r %','Error s %']
        roots = [_fz(z) for z in res['raices']]
        def f(x):
            v=0
            for c in coef: v=v*x+c
            return v
        residuals = [abs(f(z)) for z in res['raices']]
        real_roots = [z.real for z in res['raices'] if abs(z.imag)<1e-9]
        a, b = (min(real_roots)-2,max(real_roots)+2) if real_roots else (-5,5)
        title = 'P(x) = ' + texto_polinomio(coef)
    else:
        raise ValueError('Método desconocido.')
    points=[]
    for j in range(301):
        x=a+(b-a)*j/300
        try:
            y=f(x)
            points.append([x,y if math.isfinite(y) else None])
        except (ValueError,OverflowError,ZeroDivisionError): points.append([x,None])
    return dict(res=res, rows=rows, headers=headers, roots=roots, residuals=residuals,
                points=points, title=title, convergio=res['convergio'], pasos=desarrollo(res,d['metodo'], d['expr']))


@app.post('/api/grafica')
def muestrear_grafica():
    """Reevalúa la función al explorar otra región; no ejecuta texto como código."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error='Datos de gráfica inválidos.'), 400
    try:
        xmin, xmax = float(datos['xmin']), float(datos['xmax'])
        if not all(math.isfinite(x) and abs(x)<=1e12 for x in (xmin,xmax)) or not xmin<xmax:
            raise ValueError('Intervalo de gráfica inválido.')
        if datos.get('metodo') == 'biseccion':
            f = crear_funcion(str(datos.get('expr','')))
        elif datos.get('metodo') == 'bairstow':
            coef = extraer_coeficientes(str(datos.get('coef','')))
            def f(x):
                y=0.0
                for c in coef: y=y*x+c
                return y
        else:
            raise ValueError('Método inválido.')
        puntos=[]
        for j in range(801):
            x=xmin+(xmax-xmin)*j/800
            try:
                y=f(x)
                puntos.append([x,y if math.isfinite(y) else None])
            except (ValueError,ZeroDivisionError,OverflowError,TypeError):
                puntos.append([x,None])
        return jsonify(puntos=puntos)
    except (KeyError,TypeError,ValueError,OverflowError,RecursionError) as exc:
        return jsonify(error=str(exc)),400


@app.route('/', methods=['GET','POST'])
def index():
    d=DEFAULTS.copy()
    result=error=None
    status=200
    if request.method=='POST':
        d.update({k:request.form.get(k,v) for k,v in DEFAULTS.items()})
        try:
            result=calcular(d)
            if request.form.get('accion')=='pdf':
                from informe_pdf import generar_pdf
                return Response(generar_pdf(d,result),mimetype='application/pdf',headers={'Content-Disposition':'attachment; filename=RaizLab_ejercicio.pdf'})
            if request.form.get('accion')=='csv':
                out=io.StringIO(newline='')
                w=csv.writer(out)
                w.writerow(['Método',d['metodo']]); w.writerow(['Convergió',result['convergio']])
                w.writerow(['Tolerancia %',d['tol']])
                w.writerow(['Raíz','Residuo absoluto'])
                w.writerows(zip(result['roots'],result['residuals']))
                w.writerow([]); w.writerow(result['headers']); w.writerows(result['rows'])
                return Response('\ufeff'+out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=raizlab_resultados.csv'})
        except (ValueError,ZeroDivisionError,OverflowError,RecursionError) as exc:
            error='Revisa los datos: '+str(exc)
            status=400
    return render_template('index.html',d=d,result=result,error=error),status


if __name__=='__main__':
    app.run(host='127.0.0.1',port=5000,debug=False)
