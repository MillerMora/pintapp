## Alcance y límites de la fase 1

- **No incluido a propósito:** inicio de sesión, gestión de usuarios y operaciones de stock del trabajador o
  del administrador (el caso de uso las marca como aun no esta claro). Tampoco el aprobado/rechazado del carro del
  frontend ni la confirmación de compra, porque no está confirmado.
- **Validación de la foto:** es técnica (formato, tamaño, resolución). No detecta si hay una persona de
  cuerpo completo; eso requiere un modelo de visión (por ejemplo MediaPipe) y se añadiría como un paso más
  en `service/photo.py`.
- **Estado en memoria y un solo proceso:** sesiones, cola y resultados se pierden al reiniciar y no se
  comparten entre procesos. Para varios procesos o servidores hay que implementar `SessionStore`/`JobStore`
  sobre Redis y una cola externa. Se levanta **un** proceso de Uvicorn (sin `--workers`).
- **Generador simulado:** la imagen resultante es la foto con rectángulos de color sobre cada zona y la
  leyenda "SIMULACION"; sirve para probar el flujo, no para evaluar calidad visual.
- **Pruebas:** este proyecto no incluye pruebas (decisión de la fase actual).
