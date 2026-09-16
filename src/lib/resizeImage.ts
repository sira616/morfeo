/**
 * Redimensiona una imagen a un cuadrado pequeño y la devuelve como data URL.
 *
 * Se hace en el navegador y no en el servidor por dos motivos. Uno práctico: una foto
 * del carrete son varios MB y mandarla entera para que el servidor la encoja es tirar
 * ancho de banda; aquí sale ya en decenas de KB. Uno de seguridad: dibujar la imagen en
 * un canvas y volver a exportarla deja solo píxeles recomprimidos, sin los metadatos ni
 * la posible carga escondida del fichero original. El backend valida igualmente (no se
 * fía del cliente), pero lo que se guarda de un uso normal ya viene limpio.
 *
 * Recorta al centro (cover) para que no deforme, y exporta JPEG —que iOS Safari sabe
 * generar siempre desde canvas, a diferencia de WebP en versiones viejas—.
 */
const SIZE = 256
const QUALITY = 0.85

export async function resizeImageToDataUrl(file: File): Promise<string> {
  const bitmap = await loadBitmap(file)
  try {
    const canvas = document.createElement('canvas')
    canvas.width = SIZE
    canvas.height = SIZE
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('No se pudo procesar la imagen.')

    // Recorte cover: se toma el cuadrado central de la imagen y se escala a SIZE.
    const lado = Math.min(bitmap.width, bitmap.height)
    const sx = (bitmap.width - lado) / 2
    const sy = (bitmap.height - lado) / 2
    ctx.drawImage(bitmap, sx, sy, lado, lado, 0, 0, SIZE, SIZE)

    return canvas.toDataURL('image/jpeg', QUALITY)
  } finally {
    if ('close' in bitmap) bitmap.close()
  }
}

/**
 * `createImageBitmap` es lo directo, pero no está en todos los navegadores; el respaldo
 * con `<img>` y un object URL funciona en cualquiera.
 */
async function loadBitmap(file: File): Promise<ImageBitmap | HTMLImageElement> {
  if (typeof createImageBitmap === 'function') {
    return createImageBitmap(file)
  }
  const url = URL.createObjectURL(file)
  try {
    const img = new Image()
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = () => reject(new Error('No se pudo leer la imagen.'))
      img.src = url
    })
    return img
  } finally {
    URL.revokeObjectURL(url)
  }
}
