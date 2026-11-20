"""Informe completo descargable, generado en memoria y sin navegador."""
import io
import math
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Line, String, PolyLine

pdfmetrics.registerFont(TTFont('RaizLab',str(Path(__file__).parent/'fonts'/'DejaVuSans.ttf')))


def grafica(puntos):
    w,h=740,190
    dibujo=Drawing(w,h)
    validos=[(x,y) for x,y in puntos if y is not None and math.isfinite(y)]
    if not validos:
        dibujo.add(String(30,120,'No hay puntos finitos para graficar.',fontName='RaizLab',fontSize=10))
        return dibujo
    x0,x1=puntos[0][0],puntos[-1][0]
    y0,y1=min(0,min(y for x,y in validos)),max(0,max(y for x,y in validos))
    if y0==y1:y0-=1;y1+=1
    margen=(y1-y0)*.08;y0-=margen;y1+=margen
    X=lambda x:65+(x-x0)/(x1-x0)*(w-90)
    Y=lambda y:35+(y-y0)/(y1-y0)*(h-60)
    for i in range(6):
        x=x0+(x1-x0)*i/5;y=y0+(y1-y0)*i/5
        dibujo.add(Line(X(x),35,X(x),h-25,strokeColor=colors.HexColor('#e4e4ed')))
        dibujo.add(Line(65,Y(y),w-25,Y(y),strokeColor=colors.HexColor('#e4e4ed')))
        dibujo.add(String(X(x),18,f'{x:.4g}',textAnchor='middle',fontName='RaizLab',fontSize=8))
        dibujo.add(String(58,Y(y)-3,f'{y:.4g}',textAnchor='end',fontName='RaizLab',fontSize=8))
    dibujo.add(Line(65,Y(0),w-25,Y(0),strokeColor=colors.grey))
    if x0<=0<=x1:dibujo.add(Line(X(0),35,X(0),h-25,strokeColor=colors.grey))
    tramo=[]
    def guardar():
        if len(tramo)>=4:dibujo.add(PolyLine(tramo[:],strokeColor=colors.HexColor('#7043b6'),strokeWidth=1.5))
    for x,y in puntos:
        if y is None or not math.isfinite(y):guardar();tramo=[];continue
        if tramo and abs(Y(y)-tramo[-1])>h*1.5:guardar();tramo=[]
        tramo.extend((X(x),Y(y)))
    guardar()
    dibujo.add(String(w-20,18,'x',fontName='RaizLab',fontSize=9))
    dibujo.add(String(20,h-15,'f(x)',fontName='RaizLab',fontSize=9))
    return dibujo


def generar_pdf(d, resultado):
    salida=io.BytesIO()
    doc=SimpleDocTemplate(salida,pagesize=landscape(A4),rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=38,title='RaízLab - Informe del ejercicio',author='RaízLab')
    estilos=getSampleStyleSheet()
    for estilo in estilos.byName.values():estilo.fontName='RaizLab'
    estilos['Normal'].fontSize=9;estilos['Normal'].leading=14
    estilos['Title'].textColor=colors.HexColor('#463079');estilos['Title'].fontSize=22
    estilos.add(ParagraphStyle('Operacion',parent=estilos['Normal'],spaceAfter=8,leftIndent=12))
    estilos.add(ParagraphStyle('Celda',parent=estilos['Normal'],fontSize=7,leading=10))
    def p(texto,estilo='Normal'):return Paragraph(escape(str(texto)),estilos[estilo])
    contenido=[p('RaízLab | Informe del ejercicio','Title'),p('Método: '+('Bisección' if d['metodo']=='biseccion' else 'Bairstow'),'Heading2'),p(resultado['title']),Spacer(1,10),p(f"Tolerancia: {d['tol']} % | Máximo solicitado: {d['it']} iteraciones"),p('Estado: '+('criterio alcanzado o solución directa' if resultado['convergio'] else 'sin convergencia completa; resultados aproximados o parciales'))]
    if d['metodo']=='biseccion':
        res=resultado['res'];contenido+=[p(f"Intervalo inicial: [{d['a']}, {d['b']}]. f(a) = {res['fa0']:.8g}; f(b) = {res['fb0']:.8g}."),p('La bisección requiere continuidad en el intervalo. La tolerancia mide el cambio entre aproximaciones.')]
    else:
        contenido+=[p('Polinomio ingresado: '+d['coef']),p('Coeficientes detectados: '+str(resultado['res']['coef'])),p(f"Valores iniciales: r = {d['r']}; s = {d['s']}. El máximo se aplica por factor.")]
    contenido.append(p('Raíces y comprobación','Heading2'))
    for i,(raiz,residuo) in enumerate(zip(resultado['roots'],resultado['residuals']),1):
        contenido.append(p(f'x{i} ≈ {raiz}     |f(x{i})| ≈ {residuo:.8g}'))
    if not resultado['roots']:contenido.append(p('No se obtuvieron raíces confirmadas.'))
    contenido.extend([p('Gráfica de la función','Heading2'),grafica(resultado['points']),p('Vista inicial del ejercicio sobre el eje real. La gráfica es muestreada; las raíces complejas no se representan como cortes con el eje x.')])
    contenido.extend([PageBreak(),p('Desarrollo paso a paso','Title'),p('Se incluyen todas las iteraciones. Los números del procedimiento se muestran con ocho cifras significativas; los cálculos conservan la precisión de Python.')])
    if not resultado['pasos']:
        contenido.append(p('No se necesitaron iteraciones: '+('se encontró una raíz exacta en un extremo del intervalo.' if d['metodo']=='biseccion' else 'se resolvió directamente el polinomio cuadrático.')))
    for paso in resultado['pasos']:
        contenido.append(p(paso['titulo'],'Heading1'))
        for j,(titulo,texto) in enumerate(paso['bloques']):
            contenido.append(p(titulo,'Heading3'))
            # Separar operaciones sin romper puntos decimales.
            import re
            for linea in re.split(r';\s*|(?<=[.])\s+(?=[A-ZÁÉÍÓÚ¿])',texto):
                contenido.append(p(linea,'Operacion'))
            if j==0:
                for operacion in paso['extras']:contenido.append(p(operacion,'Operacion'))
    fin=resultado['res'].get('final')
    if fin:
        contenido.append(p('Resolución del polinomio restante','Heading2'))
        if fin['grado']==2:
            a0,a1,a2=fin['a']
            contenido.append(p(f'x = (−({a1:.8g}) ± √(({a1:.8g})² − 4({a2:.8g})({a0:.8g}))) / (2({a2:.8g}))','Operacion'))
        else:
            contenido.append(p(f"x = −({fin['a'][0]:.8g}) / ({fin['a'][1]:.8g})",'Operacion'))
        contenido.append(p('Raíces: '+', '.join(str(z) for z in fin['raices'])+' (j es la unidad imaginaria).'))
    contenido+=[PageBreak(),p('Tabla completa de iteraciones','Title')]
    filas=[[p(h,'Celda') for h in resultado['headers']]]
    for fila in resultado['rows']:
        filas.append([p('—' if v is None else (f'{v:.8g}' if isinstance(v,(int,float)) else v),'Celda') for v in fila])
    if len(filas)>1:
        ancho=doc.width
        widths=[ancho*.11]*6+[ancho*.34] if d['metodo']=='biseccion' else [ancho/8]*8
        tabla=LongTable(filas,colWidths=widths,repeatRows=1,hAlign='LEFT')
        tabla.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#ece5f8')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7f6fb')]),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#d9d5e5')),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        contenido.append(tabla)
    else:contenido.append(p('Solución directa: no hay filas de iteraciones.'))
    def pie(canvas,documento):
        canvas.saveState();canvas.setFont('RaizLab',8);canvas.setFillColor(colors.grey);canvas.drawString(40,20,'RaízLab | '+d['metodo']);canvas.drawRightString(landscape(A4)[0]-40,20,f'Página {documento.page}');canvas.restoreState()
    doc.build(contenido,onFirstPage=pie,onLaterPages=pie)
    return salida.getvalue()
