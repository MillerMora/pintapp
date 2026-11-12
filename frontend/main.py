import tkinter as tk
from PIL import Image, ImageTk

ventana = tk.Tk()
ventana.title("Pintapp")
ventana.geometry("1200x700")
ventana.config(bg="#eeeeee")

carrito = []
panel_carro = None
contenido_carro = None
ancho_carro = 0
posicion_x = 0


# ==========================================
# FUNCIONES DEL CARRO DESPLEGABLE
# ==========================================

def agregar_carro(ropa):
    carrito.append({
        "nombre": ropa,
        "estado": None
    })

    if panel_carro is not None:
        refrescar_carro()


def cambiar_estado(indice, estado):
    carrito[indice]["estado"] = estado
    refrescar_carro()


def eliminar_ropa(indice):
    carrito.pop(indice)
    refrescar_carro()


def refrescar_carro():

    for elemento in contenido_carro.winfo_children():
        elemento.destroy()

    for indice, ropa in enumerate(carrito):

        fila = tk.Frame(
            contenido_carro,
            bg="#eeeeee",
            pady=8
        )

        fila.pack(fill="x", padx=10, pady=4)

        fila.grid_columnconfigure(0, weight=1)
        fila.grid_columnconfigure(1, minsize=45)
        fila.grid_columnconfigure(2, minsize=45)
        fila.grid_columnconfigure(3, minsize=40)

        nombre = tk.Label(
            fila,
            text=ropa["nombre"],
            bg="#eeeeee",
            anchor="w",
            width=22,
            font=("Arial", 10)
        )

        nombre.grid(row=0, column=0, sticky="ew", padx=5)

        # Boton aprobado
        tk.Button(
            fila,
            text="✓",
            width=3,
            bg="#a8dfae" if ropa["estado"] == "aprobado" else "white",
            command=lambda i=indice: cambiar_estado(i, "aprobado")
        ).grid(row=0, column=1, padx=2)

        # Boton rechazado
        tk.Button(
            fila,
            text="X",
            width=3,
            bg="#efa3a3" if ropa["estado"] == "rechazado" else "white",
            command=lambda i=indice: cambiar_estado(i, "rechazado")
        ).grid(row=0, column=2, padx=2)

        # Eliminar prenda
        tk.Button(
            fila,
            text="-",
            width=3,
            command=lambda i=indice: eliminar_ropa(i)
        ).grid(row=0, column=3, padx=2)


def cerrar_carro():

    if panel_carro is None:
        return

    deslizar_cerrar()


def deslizar_abrir(x):

    global posicion_x

    if panel_carro is None:
        return

    posicion_x = min(x + 30, 0)

    panel_carro.geometry(
        f"{ancho_carro}x{ventana.winfo_height()}"
        f"+{ventana.winfo_rootx() + posicion_x}"
        f"+{ventana.winfo_rooty()}"
    )

    if posicion_x < 0:
        ventana.after(10, lambda: deslizar_abrir(posicion_x))


def deslizar_cerrar():

    global posicion_x

    if panel_carro is None:
        return

    posicion_x = max(posicion_x - 30, -ancho_carro)

    panel_carro.geometry(
        f"{ancho_carro}x{ventana.winfo_height()}"
        f"+{ventana.winfo_rootx() + posicion_x}"
        f"+{ventana.winfo_rooty()}"
    )

    if posicion_x > -ancho_carro:
        ventana.after(10, deslizar_cerrar)

    else:
        finalizar_cierre()


def finalizar_cierre():

    global panel_carro, contenido_carro

    if panel_carro is not None:
        panel_carro.destroy()

    panel_carro = None
    contenido_carro = None

    try:
        ventana.attributes("-alpha", 1.0)
    except tk.TclError:
        pass


def abrir_carro():

    global panel_carro
    global contenido_carro
    global ancho_carro
    global posicion_x

    if panel_carro is not None:
        return

    ventana.update_idletasks()

    ancho_carro = int(ventana.winfo_width() * 0.40)
    posicion_x = -ancho_carro

    # Oscurecer aplicacion
    try:
        ventana.attributes("-alpha", 0.55)
    except tk.TclError:
        pass

    # Ventana superpuesta
    panel_carro = tk.Toplevel(ventana)
    panel_carro.overrideredirect(True)
    panel_carro.configure(bg="white")

    panel_carro.geometry(
        f"{ancho_carro}x{ventana.winfo_height()}"
        f"+{ventana.winfo_rootx() - ancho_carro}"
        f"+{ventana.winfo_rooty()}"
    )

    panel_carro.lift()

    # Encabezado
    encabezado = tk.Frame(panel_carro, bg="#333333")
    encabezado.pack(fill="x")

    tk.Label(
        encabezado,
        text="CARRO / LISTA DE ROPA",
        bg="#333333",
        fg="white",
        font=("Arial", 15, "bold")
    ).pack(side="left", padx=15, pady=15)

    tk.Button(
        encabezado,
        text="X",
        bg="#333333",
        fg="white",
        command=cerrar_carro
    ).pack(side="right", padx=15)

    # Columnas de aprobacion
    columnas = tk.Frame(panel_carro, bg="#cccccc")
    columnas.pack(fill="x", padx=10, pady=5)

    columnas.grid_columnconfigure(0, weight=1)
    columnas.grid_columnconfigure(1, minsize=45)
    columnas.grid_columnconfigure(2, minsize=45)
    columnas.grid_columnconfigure(3, minsize=40)

    tk.Label(
        columnas,
        text="PRENDA",
        bg="#cccccc",
        font=("Arial", 9, "bold"),
        anchor="w"
    ).grid(row=0, column=0, sticky="ew", padx=5)

    tk.Label(
        columnas,
        text="OK",
        bg="#cccccc"
    ).grid(row=0, column=1)

    tk.Label(
        columnas,
        text="NO",
        bg="#cccccc"
    ).grid(row=0, column=2)

    tk.Label(
        columnas,
        text="DEL",
        bg="#cccccc"
    ).grid(row=0, column=3)

    # Contenido de la lista
    contenido_carro = tk.Frame(panel_carro, bg="white")
    contenido_carro.pack(fill="both", expand=True)

    refrescar_carro()

    tk.Button(
        panel_carro,
        text="CONFIRMAR ROPA A COMPRAR",
        bg="magenta3",
        fg="white",
        font=("Arial", 11, "bold"),
        command=lambda: print("Ropa confirmada:", carrito)
    ).pack(fill="x", padx=10, pady=15)

    # Animacion
    deslizar_abrir(posicion_x)


# ==========================================
# ENCABEZADO PRINCIPAL
# ==========================================

encabezado = tk.Frame(ventana, bg="#eeeeee")
encabezado.pack(fill="x", padx=15, pady=10)

tk.Button(
    encabezado,
    text="☰ CARRO / LISTA",
    font=("Arial", 11, "bold"),
    command=abrir_carro
).pack(side="left")

tk.Label(
    encabezado,
    text="PINTAPP",
    bg="#eeeeee",
    font=("Arial", 24, "bold")
).pack(side="top")


# ==========================================
# CONTENEDOR PRINCIPAL
# ==========================================

principal = tk.Frame(ventana, bg="#eeeeee")
principal.pack(fill="both", expand=True, padx=10, pady=10)


# ==========================================
# CAMARA / CENTRO
# ==========================================

centro = tk.Frame(
    principal,
    bg="white",
    bd=2,
    relief="solid"
)

centro.pack(side="left", fill="both", expand=True, padx=5)

tk.Label(
    centro,
    text="DETECCION DE POSE",
    bg="white",
    font=("Arial", 14, "bold")
).pack(pady=15)

camara = tk.Frame(
    centro,
    bg="#d3d3d3",
    bd=2,
    relief="sunken"
)

camara.pack(fill="both", expand=True, padx=15, pady=10)

tk.Label(
    camara,
    text="Aqui se mostrara la camara\ny la deteccion de MediaPipe",
    bg="#d3d3d3",
    font=("Arial", 14)
).pack(expand=True)

tk.Button(
    centro,
    text="CAMARA",
    bg="magenta3",
    fg="white",
    font=("Arial", 14, "bold"),
    command=lambda: print("Abrir camara")
).pack(pady=10)


# ==========================================
# CATALOGO DE ROPA
# ==========================================

catalogo = tk.Frame(
    principal,
    bg="white",
    bd=2,
    relief="solid",
    width=390
)

catalogo.pack(side="right", fill="y", padx=5)
catalogo.pack_propagate(False)

tk.Label(
    catalogo,
    text="CATALOGO DE ROPA",
    bg="white",
    font=("Arial", 14, "bold")
).pack(pady=15)


# Prendas y colores de prototipo

ropas = {
    "Camisas": [
        ("Camisa blanca", "#eeeeee"),
        ("Camisa negra", "#333333"),
        ("Camisa azul", "#547da8")
    ],

    "Pantalones": [
        ("Jean", "#416b99"),
        ("Pantalon negro", "#333333"),
        ("Pantalon beige", "#c9ad83")
    ],

    "Chaquetas": [
        ("Chaqueta cuero", "#49352c"),
        ("Chaqueta jean", "#547da8")
    ],

    "Zapatos": [
        ("Tenis", "#eeeeee"),
        ("Botas", "#49352c")
    ],

    "Camisetas": [
        ("Camiseta blanca", "#eeeeee"),
        ("Camiseta negra", "#333333")
    ]
}


def desplegar_categoria(boton, panel):

    if panel.winfo_ismapped():
        panel.pack_forget()
        boton.config(text="▼")

    else:
        panel.pack(fill="x", padx=5, pady=5)
        boton.config(text="▲")


for categoria, prendas in ropas.items():

    bloque = tk.Frame(catalogo, bg="white")
    bloque.pack(fill="x", padx=10, pady=5)

    # Nombre de categoria
    fila = tk.Frame(bloque, bg="white")
    fila.pack(fill="x")

    tk.Label(
        fila,
        text=categoria,
        bg="white",
        font=("Arial", 11, "bold")
    ).pack(side="left")

    # Panel de prendas debajo del nombre
    panel = tk.Frame(bloque, bg="#eeeeee")

    boton = tk.Button(
        fila,
        text="▼",
        command=lambda b=None, p=None: None
    )

    boton.pack(side="right")

    boton.config(
        command=lambda b=boton, p=panel:
        desplegar_categoria(b, p)
    )

    # Cuadros horizontales de prendas
    for nombre, color in prendas:

        tarjeta = tk.Frame(
            panel,
            bg="white",
            bd=1,
            relief="solid"
        )

        tarjeta.pack(side="left", padx=4, pady=5)

        # Prototipo visual de la prenda
        muestra = tk.Frame(
            tarjeta,
            bg=color,
            width=55,
            height=55
        )

        muestra.pack(padx=5, pady=5)
        muestra.pack_propagate(False)

        tk.Label(
            tarjeta,
            text=nombre,
            bg="white",
            font=("Arial", 7),
            wraplength=65
        ).pack(pady=3)

        tk.Button(
            tarjeta,
            text="Agregar",
            font=("Arial", 8),
            command=lambda n=nombre: agregar_carro(n)
        ).pack(pady=3)


# ==========================================
# ICONO
# ==========================================

try:
    icono = Image.open("frontend/img/pintapp.png")
    icono_tkinter = ImageTk.PhotoImage(icono)
    ventana.iconphoto(False, icono_tkinter)

except:
    print("No se encontro el icono de Pintapp")


ventana.mainloop()