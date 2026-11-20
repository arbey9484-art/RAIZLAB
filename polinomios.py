"""Conversión de polinomios a coeficientes sin eval ni ejecución de código."""
import ast
import math
import re


def extraer_coeficientes(texto):
    if not isinstance(texto, str) or not texto.strip() or len(texto)>500:
        raise ValueError('Escribe un polinomio de hasta 500 caracteres.')
    if ',' in texto:  # Compatibilidad con ejercicios guardados anteriormente.
        try:
            coef=[float(x.strip()) for x in texto.split(',')]
        except ValueError:
            raise ValueError('Usa punto para decimales. Ejemplo: 2.5*x^2 - x + 1.')
    else:
        texto=texto.strip().replace('−','-').replace('×','*').replace('·','*')
        superindices=str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹','0123456789')
        texto=re.sub('[⁰¹²³⁴⁵⁶⁷⁸⁹]+',lambda m:'**'+m[0].translate(superindices),texto)
        texto=texto.replace('^','**')
        texto=re.sub(r'(?<=[0-9)])\s*(?=x|\()', '*', texto)
        texto=re.sub(r'(?<=x)\s*(?=\()', '*', texto)
        try:
            arbol=ast.parse(texto,mode='eval')
        except (SyntaxError,RecursionError):
            raise ValueError('Polinomio inválido. Ejemplo: x^3 - 6x^2 + 11x - 6.')
        if len(list(ast.walk(arbol)))>160:
            raise ValueError('El polinomio tiene demasiadas operaciones.')

        def limpiar(p):
            while len(p)>1 and p[-1]==0:p.pop()
            if len(p)>21 or not all(math.isfinite(x) and abs(x)<=1e12 for x in p):
                raise ValueError('Se admiten grados hasta 20 y coeficientes de magnitud hasta 10^12.')
            return p

        def sumar(a,b,signo=1):
            c=[0.] * max(len(a),len(b))
            for i,x in enumerate(a):c[i]+=x
            for i,x in enumerate(b):c[i]+=signo*x
            return limpiar(c)

        def multiplicar(a,b):
            if len(a)+len(b)-1>21:
                raise ValueError('El grado máximo admitido es 20.')
            c=[0.]*(len(a)+len(b)-1)
            for i,x in enumerate(a):
                for j,y in enumerate(b):c[i+j]+=x*y
            return limpiar(c)

        def convertir(n):
            if isinstance(n,ast.Expression):return convertir(n.body)
            if isinstance(n,ast.Constant) and type(n.value) in (int,float):return limpiar([float(n.value)])
            if isinstance(n,ast.Name) and n.id=='x':return [0.,1.]
            if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
                return [x*(-1 if isinstance(n.op,ast.USub) else 1) for x in convertir(n.operand)]
            if isinstance(n,ast.BinOp):
                a,b=convertir(n.left),convertir(n.right)
                if isinstance(n.op,ast.Add):return sumar(a,b)
                if isinstance(n.op,ast.Sub):return sumar(a,b,-1)
                if isinstance(n.op,ast.Mult):return multiplicar(a,b)
                if isinstance(n.op,ast.Div):
                    if len(b)!=1 or b[0]==0:raise ValueError('Solo puedes dividir por una constante distinta de cero.')
                    return limpiar([x/b[0] for x in a])
                if isinstance(n.op,ast.Pow):
                    if len(b)!=1 or not b[0].is_integer() or not 0<=b[0]<=20:
                        raise ValueError('Las potencias deben ser enteros entre 0 y 20.')
                    c=[1.]
                    for _ in range(int(b[0])):c=multiplicar(c,a)
                    return c
            raise ValueError('Usa solo x, números, paréntesis y + - * / ^. Bairstow requiere un polinomio.')
        try:
            coef=list(reversed(convertir(arbol)))
        except (OverflowError,RecursionError):
            raise ValueError('El polinomio excede los límites numéricos.')
    if not 3<=len(coef)<=21 or coef[0]==0 or not all(math.isfinite(c) and abs(c)<=1e12 for c in coef):
        raise ValueError('Bairstow requiere un polinomio de grado 2 a 20, con coeficientes finitos de magnitud hasta 10^12.')
    return coef
