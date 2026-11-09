import tkinter as tk
from PIL import Image, ImageTk
    
ventana = tk.Tk()
ventana.title("pintapp")
ventana.geometry("500x500")

#orden de los elementos en la ventana

titulo = "pintapp"
texto="presiona el botón para abrir la cámara para escanear tu Pose para detectar la pose del cuerpo con MediaPipe "
#botón de abrir la cámara para escanear la pose del cuerpo
#cuadro de x tamaño (aun por definir) del cuadro que mostrara la cámara y la detección de la pose del cuerpo
 
# wraplength=350 significa que al llegar a 350 píxeles de ancho, el texto saltará
etiqueta = tk.Label(ventana, text=titulo, wraplength=350, bg="goldenrod2", fg="black", font=("Morp Caps Outline", 28))
etiqueta.pack()

etiqueta = tk.Label(ventana, text=texto, wraplength=350, bg="lightgray", fg="black", font=("Jump Streets", 28))
etiqueta.pack()#muestra el texto en la ventana

#icono de la ventana
# 1. Cargar la imagen con Pillow
icono = Image.open("frontend/img/pintapp.png")

# 2. Convertirla usando la variable correcta (imagen_original)
icono_tkinter = ImageTk.PhotoImage(icono)

# 3. Aplicar el icono
ventana.iconphoto(False, icono_tkinter)

button = tk.Button(ventana, text="Cámara", bg="magenta3", fg="goldenrod2", font=("Jump Streets", 18), command=lambda: print("Botón presionado"))


button.pack()# muestra el botón en la ventana

etiqueta = tk.Label(ventana, text="aquí se mostrara la cámara y la detección de la pose del cuerpo")
etiqueta.pack()#muestra el texto en la ventana


ventana.mainloop()