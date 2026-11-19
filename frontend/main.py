import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from PIL import Image, ImageTk

try:
    import cv2
    import mediapipe as mp
except ImportError:
    cv2 = None
    mp = None

MODELO_POSE_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/1/pose_landmarker_full.task"
)
BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "img"


ventana = tk.Tk()
ventana.title("Pintapp")
ventana.geometry("1200x700")
ventana.config(bg="#eeeeee")

captura_camara = None
detector_pose = None
camara_activa = False
imagen_camara = None
marca_tiempo_camara = 0

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


def obtener_modelo_pose():
    ruta_modelo = Path.home() / ".pintapp" / "pose_landmarker_full.task"
    if ruta_modelo.exists():
        return ruta_modelo

    ruta_modelo.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(MODELO_POSE_URL, timeout=30) as respuesta:
            ruta_modelo.write_bytes(respuesta.read())
    except (OSError, TimeoutError, URLError) as error:
        ruta_modelo.unlink(missing_ok=True)
        raise RuntimeError(
            "No se pudo descargar el modelo de MediaPipe."
        ) from error

    return ruta_modelo


def iniciar_camara():
    global captura_camara, detector_pose, camara_activa, marca_tiempo_camara

    if cv2 is None or mp is None:
        messagebox.showerror(
            "Dependencias faltantes",
            "Instala las dependencias del proyecto con:\n"
            "uv sync"
        )
        return

    try:
        ruta_modelo = obtener_modelo_pose()
        opciones_pose = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(ruta_modelo)
            ),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        detector_pose = mp.tasks.vision.PoseLandmarker.create_from_options(
            opciones_pose
        )
    except (OSError, RuntimeError, ValueError) as error:
        messagebox.showerror("MediaPipe no disponible", str(error))
        return

    captura_camara = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not captura_camara.isOpened():
        captura_camara.release()
        captura_camara = None
        detector_pose.close()
        detector_pose = None
        messagebox.showerror(
            "Cámara no disponible",
            "No se pudo abrir la cámara. Verifica que esté conectada y "
            "que ninguna otra aplicación la esté usando."
        )
        return

    camara_activa = True
    marca_tiempo_camara = 0
    boton_camara.config(text="DETENER CÁMARA")
    texto_camara.config(text="")
    actualizar_camara()


def detener_camara():
    global captura_camara, detector_pose, camara_activa, imagen_camara

    camara_activa = False
    if captura_camara is not None:
        captura_camara.release()
        captura_camara = None
    if detector_pose is not None:
        detector_pose.close()
        detector_pose = None

    imagen_camara = None
    texto_camara.config(
        image="",
        text="Presiona CAMARA para iniciar\nla detección de pose"
    )
    boton_camara.config(text="CAMARA")


def alternar_camara():
    if camara_activa:
        detener_camara()
    else:
        iniciar_camara()


def actualizar_camara():
    global imagen_camara, marca_tiempo_camara

    if not camara_activa or captura_camara is None:
        return

    lectura_exitosa, frame = captura_camara.read()
    if not lectura_exitosa:
        detener_camara()
        messagebox.showerror(
            "Error de cámara",
            "La cámara dejó de entregar imágenes."
        )
        return

    frame = cv2.flip(frame, 1)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    imagen_mp = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=frame_rgb
    )
    marca_tiempo_camara += 33
    timestamp = marca_tiempo_camara
    resultado = detector_pose.detect_for_video(imagen_mp, timestamp)

    if resultado.pose_landmarks:
        alto_frame, ancho_frame = frame_rgb.shape[:2]
        for landmarks in resultado.pose_landmarks:
            for conexion in mp.tasks.vision.PoseLandmarksConnections.POSE_LANDMARKS:
                inicio = landmarks[conexion.start]
                fin = landmarks[conexion.end]
                punto_inicio = (
                    int(inicio.x * ancho_frame),
                    int(inicio.y * alto_frame)
                )
                punto_fin = (
                    int(fin.x * ancho_frame),
                    int(fin.y * alto_frame)
                )
                cv2.line(
                    frame_rgb,
                    punto_inicio,
                    punto_fin,
                    (0, 255, 0),
                    2
                )
            for landmark in landmarks:
                punto = (
                    int(landmark.x * ancho_frame),
                    int(landmark.y * alto_frame)
                )
                cv2.circle(frame_rgb, punto, 4, (255, 0, 0), -1)

    imagen = Image.fromarray(frame_rgb)
    ancho = max(camara.winfo_width(), 1)
    alto = max(camara.winfo_height(), 1)
    imagen.thumbnail((ancho, alto), Image.Resampling.LANCZOS)
    imagen_camara = ImageTk.PhotoImage(imagen)
    texto_camara.config(image=imagen_camara, text="")
    ventana.after(15, actualizar_camara)


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
    panel_carro.place_configure(
        x=posicion_x,
        y=0,
        width=ancho_carro,
        relheight=1
    )

    if posicion_x < 0:
        ventana.after(10, lambda: deslizar_abrir(posicion_x))


def deslizar_cerrar():

    global posicion_x

    if panel_carro is None:
        return

    posicion_x = max(posicion_x - 30, -ancho_carro)
    panel_carro.place_configure(
        x=posicion_x,
        y=0,
        width=ancho_carro,
        relheight=1
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

    # Panel integrado en la ventana principal, sin transparencia global.
    panel_carro = tk.Frame(ventana, bg="white", bd=1, relief="solid")
    panel_carro.place(
        x=posicion_x,
        y=0,
        width=ancho_carro,
        relheight=1
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

    # Animacion horizontal dentro de la aplicacion
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

try:
    logo = Image.open(IMG_DIR / "Pintapp_TXT.png")
    logo.thumbnail((360, 100), Image.Resampling.LANCZOS)
    logo_tk = ImageTk.PhotoImage(logo)
    etiqueta_logo = tk.Label(
        encabezado,
        image=logo_tk,
        bg="#eeeeee"
    )
    etiqueta_logo.image = logo_tk
    etiqueta_logo.pack(side="top")
except (FileNotFoundError, OSError) as error:
    print(f"No se pudo cargar el logo de Pintapp: {error}")
    tk.Label(
        encabezado,
        text="Pintapp",
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

texto_camara = tk.Label(
    camara,
    text="Presiona CAMARA para iniciar\nla detección de pose",
    bg="#d3d3d3",
    font=("Arial", 14)
)
texto_camara.pack(expand=True)

boton_camara = tk.Button(
    centro,
    text="CAMARA",
    bg="magenta3",
    fg="white",
    font=("Arial", 14, "bold"),
    command=alternar_camara
)
boton_camara.pack(pady=10)


def cerrar_aplicacion():
    detener_camara()
    ventana.destroy()


ventana.protocol("WM_DELETE_WINDOW", cerrar_aplicacion)


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

area_catalogo = tk.Frame(catalogo, bg="white")
area_catalogo.pack(fill="both", expand=True, padx=5, pady=(0, 5))
area_catalogo.grid_rowconfigure(0, weight=1)
area_catalogo.grid_columnconfigure(0, weight=1)

lienzo_catalogo = tk.Canvas(
    area_catalogo,
    bg="white",
    highlightthickness=0
)
lienzo_catalogo.grid(row=0, column=0, sticky="nsew")

barra_catalogo = tk.Scrollbar(
    area_catalogo,
    orient="vertical",
    command=lienzo_catalogo.yview
)
lienzo_catalogo.configure(yscrollcommand=barra_catalogo.set)

contenido_catalogo = tk.Frame(lienzo_catalogo, bg="white")
ventana_catalogo = lienzo_catalogo.create_window(
    (0, 0),
    window=contenido_catalogo,
    anchor="nw"
)


def actualizar_region_catalogo(_evento=None):
    lienzo_catalogo.configure(
        scrollregion=lienzo_catalogo.bbox("all")
    )
    if contenido_catalogo.winfo_reqheight() > lienzo_catalogo.winfo_height():
        barra_catalogo.grid(row=0, column=1, sticky="ns")
    else:
        barra_catalogo.grid_remove()


def ajustar_ancho_catalogo(evento):
    lienzo_catalogo.itemconfigure(ventana_catalogo, width=evento.width)
    actualizar_region_catalogo()


def desplazar_catalogo(evento):
    widget = ventana.winfo_containing(evento.x_root, evento.y_root)
    while widget is not None:
        if widget == catalogo:
            lienzo_catalogo.yview_scroll(
                -int(evento.delta / 120),
                "units"
            )
            return "break"
        widget = widget.master


contenido_catalogo.bind("<Configure>", actualizar_region_catalogo)
lienzo_catalogo.bind("<Configure>", ajustar_ancho_catalogo)
ventana.bind_all("<MouseWheel>", desplazar_catalogo, add="+")


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

    bloque = tk.Frame(contenido_catalogo, bg="white")
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
    icono = Image.open(IMG_DIR / "pintapp_oficial.png")
    icono.thumbnail((64, 64), Image.Resampling.LANCZOS)
    icono_tkinter = ImageTk.PhotoImage(icono)
    ventana.iconphoto(False, icono_tkinter)
except (FileNotFoundError, OSError) as error:
    print(f"No se encontro el icono de Pintapp: {error}")


ventana.mainloop()