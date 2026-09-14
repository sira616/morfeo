"""Anunciar la app en la red local con un nombre propio: `morfeo.local`.

El fichero `hosts` de Windows no sirve para esto. Solo lo lee el ordenador que lo
tiene, y lo que se quiere es que el **iPhone** resuelva el nombre. En una red doméstica
sin servidor DNS propio, eso solo lo hace mDNS: el móvil pregunta «¿quién es
morfeo.local?» a la red entera y alguien contesta. Aquí contestamos nosotros.

Windows ya anuncia el nombre del equipo (`DESKTOP-LC1P85F.local` y parecidos), pero no
sabe anunciar alias, y renombrar el ordenador entero para que la app tenga el nombre
bonito es desproporcionado. Un responder propio cuesta veinte líneas.

Va dentro del proceso de la app, no en un script aparte, por lo mismo que el frontend
se sirve desde aquí: **un solo proceso que arrancar y que matar**. Si el anuncio falla
—el puerto 5353 ocupado, una red rara—, se avisa y se sigue sirviendo: quedarse sin app
por no poder registrar un nombre sería cambiar una comodidad por una caída.

**La API asíncrona no es opcional.** Esto se llama desde el lifespan de FastAPI, que
corre en el bucle de asyncio; la API síncrona de zeroconf lo bloquea y aborta con
`EventLoopBlocked`, que además llega con el mensaje vacío y no explica nada.
"""
from __future__ import annotations

import socket

_aiozc = None
_info = None


def _ip_de_la_red_local() -> str:
    """La IP con la que este equipo sale a la red, sin depender del nombre del equipo.

    El truco del socket UDP no manda nada: solo hace que el sistema elija la interfaz
    por la que saldría, y le preguntamos cuál ha elegido. Es la forma fiable de acertar
    cuando hay adaptadores virtuales (VirtualBox, Hyper-V, WSL) que también tienen IP y
    que anunciados harían que el móvil probara primero una dirección que no alcanza.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


async def announce(hostname: str, port: int) -> str:
    """Publica `hostname` apuntando a este equipo. Devuelve la IP anunciada.

    `hostname` llega como "morfeo.local"; mDNS lo quiere acabado en punto.
    """
    global _aiozc, _info

    from zeroconf import ServiceInfo
    from zeroconf.asyncio import AsyncZeroconf

    nombre = hostname.strip().rstrip(".")
    if not nombre.endswith(".local"):
        nombre = f"{nombre}.local"

    ip = _ip_de_la_red_local()

    # Se registra como servicio _http._tcp además de publicar el nombre porque es lo
    # que hace que la app salga también en los navegadores de red. Lo que de verdad
    # resuelve `morfeo.local` es `server=`: zeroconf responde a las preguntas por ese
    # nombre con la A que le damos aquí.
    _info = ServiceInfo(
        type_="_http._tcp.local.",
        name="Morfeo._http._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={"path": "/"},
        server=f"{nombre}.",
    )

    _aiozc = AsyncZeroconf()
    # `cooperating_responders` hace falta por dos motivos, y sin él el registro falla
    # con una excepción de mensaje vacío que no dice nada:
    #
    # - En este equipo ya corre el mDNSResponder de Apple (lo instalan iTunes y algún
    #   Adobe). Dos responders en la misma máquina se ven el uno al otro y cada uno
    #   toma por conflicto lo que anuncia el otro.
    # - Al reiniciar, el proceso anterior casi nunca ha podido retirar su anuncio: se
    #   mata por puerto (ver scripts\reiniciar.ps1), así que el apagado ordenado no
    #   llega a ejecutarse y el nombre sigue reclamado por un registro fantasma.
    #
    # El riesgo que se asume —registrar un nombre que otro esté usando de verdad— no
    # existe aquí: el nombre lo elegimos nosotros en la configuración.
    await _aiozc.async_register_service(
        _info, allow_name_change=True, cooperating_responders=True
    )
    return ip


async def stop() -> None:
    """Retira el anuncio. Sin esto, el nombre se queda unos minutos en la caché de los
    móviles apuntando a un servidor que ya no responde, que es peor que no anunciarlo."""
    global _aiozc, _info
    if _aiozc is None:
        return
    try:
        if _info is not None:
            await _aiozc.async_unregister_service(_info)
    finally:
        await _aiozc.async_close()
        _aiozc, _info = None, None
