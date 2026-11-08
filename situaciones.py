"""Datos de las multiplicaciones con temática de perros.

generacion_pdf.py importa las tres estructuras y las usa para construir
los enunciados.

Hay tres estructuras:

1) OBJETOS
   id: (singular, plural, genero[, emoji])
   El id es el nombre interno que usan las relaciones. El emoji es
   opcional: si se omite, o se deja vacío, el enunciado se genera
   solo con el sustantivo. Si existe, se coloca detrás del sustantivo.

2) RELACIONES
   (contexto, id_objeto_a, id_objeto_b)
   Cada relación indica una pareja de objetos que tiene sentido y el
   contexto al que pertenece. A es el número de grupos/elementos y B la
   cantidad por grupo/elemento. El resultado siempre es A × B en la
   unidad de B.

3) PLANTILLAS
   (contexto, plantilla)
   Solo se usan plantillas cuyo contexto coincida con el de la relación.

Placeholders disponibles en las plantillas:
    {a}           -> número A
    {b}           -> número B
    {a_singular}  -> objeto A en singular, con su emoji detrás
    {a_plural}    -> objeto A en plural, con su emoji detrás
    {b_singular}  -> objeto B en singular, con su emoji detrás
    {b_plural}    -> objeto B en plural, con su emoji detrás
    {a_cuantos}   -> "Cuántos" o "Cuántas" según el género de A
    {b_cuantos}   -> "Cuántos" o "Cuántas" según el género de B

A y B siempre valen entre 2 y 9, así que las cantidades siempre son
plurales. En frases como "cada perro" se usa el singular de A por
gramática, no porque la cantidad sea 1.

Para añadir variedad:
  - añade objetos nuevos,
  - añade parejas coherentes en RELACIONES,
  - añade más formas de preguntar en PLANTILLAS.

Las plantillas usan llaves de Python para los placeholders; no escribas
llaves literales dentro de una plantilla.
"""

# id: (singular, plural, género[, emoji])
OBJETOS = {
    "perro": ("perro", "perros", "m", "🐕"),
    "cachorro": ("cachorro", "cachorros", "m", "🐶"),
    "hueso": ("hueso", "huesos", "m", "🦴"),
    "collar": ("collar", "collares", "m", "📿"),
    "correa": ("correa", "correas", "f", "🔗"),
    "arnes": ("arnés", "arneses", "m", "🦺"),
    "juguete": ("juguete", "juguetes", "m", "🧸"),
    "pelota": ("pelota", "pelotas", "f", "🎾"),
    "mordedor": ("mordedor", "mordedores", "m", "🦷"),
    "golosina": ("golosina", "golosinas", "f", "🍬"),
    "galleta": ("galleta", "galletas", "f", "🍪"),
    "paquete_pienso": ("paquete de pienso", "paquetes de pienso", "m", "🛍️"),
    "saco_pienso": ("saco de pienso", "sacos de pienso", "m", "🧺"),
    "lata_comida": ("lata de comida", "latas de comida", "f", "🥫"),
    "cepillo": ("cepillo", "cepillos", "m", "🖌️"),
    "comedero": ("comedero", "comederos", "m", "🥣"),
    "bebedero": ("bebedero", "bebederos", "m", "💧"),
    "cama": ("cama", "camas", "f", "🛏️"),
    "cojin": ("cojín", "cojines", "m", "🛋️"),
    "caja": ("caja", "cajas", "f", "📦"),
    "transportin": ("transportín", "transportines", "m", "🧳"),
    "coche": ("coche", "coches", "m", "🚗"),
    "dia": ("día", "días", "m", "📅"),
    "paseo": ("paseo", "paseos", "m", "🚶"),
    "vuelta": ("vuelta", "vueltas", "f", "🔄"),
    "euro": ("euro", "euros", "m", "💶"),
}

# (contexto, id_objeto_a, id_objeto_b)
RELACIONES = [
    ("tiene", "perro", "hueso"),
    ("tiene", "perro", "collar"),
    ("tiene", "perro", "juguete"),
    ("tiene", "perro", "galleta"),
    ("tiene", "perro", "pelota"),
    ("tiene", "perro", "mordedor"),
    ("tiene", "perro", "golosina"),

    ("precio", "hueso", "euro"),
    ("precio", "collar", "euro"),
    ("precio", "juguete", "euro"),
    ("precio", "pelota", "euro"),
    ("precio", "mordedor", "euro"),
    ("precio", "correa", "euro"),
    ("precio", "arnes", "euro"),
    ("precio", "cepillo", "euro"),
    ("precio", "comedero", "euro"),
    ("precio", "bebedero", "euro"),
    ("precio", "paquete_pienso", "euro"),
    ("precio", "lata_comida", "euro"),
    ("precio", "saco_pienso", "euro"),

    ("contenedor", "cama", "cojin"),
    ("contenedor", "caja", "juguete"),
    ("contenedor", "caja", "golosina"),
    ("contenedor", "caja", "pelota"),

    ("transporte", "coche", "perro"),
    ("transporte", "coche", "cachorro"),
    ("transporte", "transportin", "cachorro"),

    ("tiempo_comer", "dia", "galleta"),
    ("tiempo_comer", "dia", "golosina"),
    ("tiempo_comer", "dia", "lata_comida"),

    ("tiempo_pasear", "dia", "paseo"),
    ("tiempo_pasear", "dia", "vuelta"),
]

# (contexto, plantilla)
PLANTILLAS = [
    ("tiene", "Hay {a} {a_plural} y cada {a_singular} tiene {b} {b_plural}. ¿{b_cuantos} {b_plural} hay?"),
    ("tiene", "Cada {a_singular} recibe {b} {b_plural}. ¿{b_cuantos} {b_plural} reciben {a} {a_plural}?"),
    ("tiene", "Cada {a_singular} tiene {b} {b_plural}. ¿{b_cuantos} {b_plural} hay entre {a} {a_plural}?"),
    ("tiene", "Tengo {a} {a_plural}. Le doy {b} {b_plural} a cada {a_singular}. ¿{b_cuantos} {b_plural} necesito?"),
    ("tiene", "{a} {a_plural} tienen {b} {b_plural} cada uno. ¿{b_cuantos} {b_plural} hay en total?"),
    ("tiene", "Hay {a} {a_plural}. A cada uno le tocan {b} {b_plural}. ¿{b_cuantos} {b_plural} son en total?"),

    ("precio", "Compro {a} {a_plural}. Cada {a_singular} cuesta {b} {b_plural}. ¿{b_cuantos} {b_plural} me he gastado?"),
    ("precio", "Compro {a} {a_plural}. Cada {a_singular} vale {b} {b_plural}. ¿{b_cuantos} {b_plural} pagaré?"),
    ("precio", "El precio de cada {a_singular} es {b} {b_plural}. ¿{b_cuantos} {b_plural} costarán {a} {a_plural}?"),
    ("precio", "Si cada {a_singular} vale {b} {b_plural}, ¿{b_cuantos} {b_plural} costarán {a} {a_plural}?"),

    ("contenedor", "En cada {a_singular} ponemos {b} {b_plural}. ¿{b_cuantos} {b_plural} necesitamos para {a} {a_plural}?"),
    ("contenedor", "En cada {a_singular} hay {b} {b_plural}. Tenemos {a} {a_plural}. ¿{b_cuantos} {b_plural} hay en total?"),
    ("contenedor", "Ponemos {b} {b_plural} en cada {a_singular}. ¿{b_cuantos} {b_plural} habrá en {a} {a_plural}?"),
    ("contenedor", "Cada {a_singular} lleva {b} {b_plural}. ¿{b_cuantos} {b_plural} llevan {a} {a_plural}?"),

    ("transporte", "En cada {a_singular} viajan {b} {b_plural}. ¿{b_cuantos} {b_plural} viajan en {a} {a_plural}?"),
    ("transporte", "En cada {a_singular} hay {b} {b_plural}. ¿{b_cuantos} {b_plural} hay en {a} {a_plural}?"),
    ("transporte", "Si en cada {a_singular} caben {b} {b_plural}, ¿{b_cuantos} {b_plural} caben en {a} {a_plural}?"),
    ("transporte", "Viajamos en {a} {a_plural}. En cada {a_singular} van {b} {b_plural}. ¿{b_cuantos} {b_plural} van en total?"),

    ("tiempo_comer", "Mi perrito come {b} {b_plural} cada {a_singular}. ¿{b_cuantos} {b_plural} comerá en {a} {a_plural}?"),
    ("tiempo_comer", "Durante {a} {a_plural}, mi perrito come {b} {b_plural} al día. ¿{b_cuantos} {b_plural} comerá en total?"),
    ("tiempo_comer", "Mi perrito come {b} {b_plural} al día. ¿{b_cuantos} {b_plural} comerá durante {a} {a_plural}?"),
    ("tiempo_comer", "En {a} {a_plural}, mi perrito come {b} {b_plural} cada día. ¿{b_cuantos} {b_plural} comerá en total?"),

    ("tiempo_pasear", "Mi perro da {b} {b_plural} cada {a_singular}. ¿{b_cuantos} {b_plural} dará en {a} {a_plural}?"),
    ("tiempo_pasear", "Durante {a} {a_plural}, mi perro da {b} {b_plural} al día. ¿{b_cuantos} {b_plural} dará en total?"),
    ("tiempo_pasear", "Mi perro da {b} {b_plural} al día. ¿{b_cuantos} {b_plural} dará durante {a} {a_plural}?"),
    ("tiempo_pasear", "Salimos a dar {b} {b_plural} cada {a_singular}. ¿{b_cuantos} {b_plural} daremos en {a} {a_plural}?"),
]
