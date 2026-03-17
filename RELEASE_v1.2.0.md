# 🎉 NovaDL v1.2.0

Nueva versión con cuatro funcionalidades que amplían el alcance de NovaDL — soporte de proxy, descarga de subtítulos, programador de descargas y tema claro opcional.

---

## ✨ Novedades

### 🔒 Soporte de proxy configurable
Configura un proxy HTTP/HTTPS/SOCKS desde `Herramientas → Descarga Avanzada`. El formato es estándar:

```
http://usuario:contraseña@host:puerto
socks5://host:puerto
```

El proxy se aplica a todas las descargas y se persiste entre sesiones. Botón **LIMPIAR** para desactivarlo al instante.

### 📝 Descarga de subtítulos con selector de idioma
Elige el idioma de subtítulos desde el combo en `Herramientas → Descarga Avanzada`. NovaDL descarga tanto los subtítulos manuales como los automáticos generados por el sitio, y los **embebe directamente** en el archivo de video.

Idiomas disponibles: `es`, `en`, `pt`, `fr`, `de`, `it`, `ja`, `ko`, `zh`, `ru`, `ar`. Selecciona `Ninguno` para desactivar.

> ℹ️ Los subtítulos embebidos solo funcionan con formatos de video (MP4, MKV). En formatos de audio se ignoran.

### ⏱ Programador de descargas
¿Quieres que NovaDL descargue a las 3am sin que tengas que estar delante? Botón **⏱ PROGRAMAR DESCARGA** en `Herramientas`. Abre una ventana emergente estilo Nexus donde eliges la hora con selector de horas y minutos (intervalos de 5 min).

- Si la hora ya pasó hoy, programa para el día siguiente automáticamente
- Muestra en el log los minutos restantes hasta la descarga
- Botón **CANCELAR PROGRAMACIÓN** para anular antes de que se ejecute
- Usa exactamente las URLs y configuración que tengas activas en ese momento

### 🌓 Tema claro opcional
Botón **☀ CLARO / OSCURO** en `Herramientas → Descarga Avanzada`. Alterna entre tema oscuro (por defecto) y tema claro en tiempo real sin reiniciar la app. La preferencia se guarda y se aplica automáticamente al abrir NovaDL.

---

## 🐛 Sin correcciones críticas

Esta versión es puramente aditiva sobre v1.1.0.

---

## 📦 Sin dependencias nuevas

No se requiere instalar nada adicional respecto a v1.1.0.

---

## 🔄 Cómo actualizar

**Opción 1 — Desde la app:** Sidebar → `ACTUALIZAR` → NovaDL se actualiza y reinicia sola.

**Opción 2 — Manual:** Descarga el instalador o el portable desde los assets de este release.

---

## 📋 Cambios técnicos

- `core/constants.py` — `APP_VERSION = "1.2.0"`, nuevas constantes `SUBTITLE_LANGS` y `THEMES`
- `core/models.py` — `QueueItem` con campos `proxy: Optional[str]` y `subtitle_lang: Optional[str]`
- `core/downloader.py` — `build_download_command` aplica `--proxy` y `--write-subs / --sub-lang / --embed-subs` desde los campos del `QueueItem`
- `ui/app.py` — vars `proxy_var`, `subtitle_var`, `theme_var`, `scheduler_active_var`, `_scheduler_timer`; método `toggle_theme()`; método `open_scheduler()` con `CTkToplevel` Nexus y `threading.Timer`; método `_run_scheduled()` que dispara `start_download` desde el hilo correcto
- `ui/tabs/tools.py` — nueva fila `DESCARGA AVANZADA / APARIENCIA` con campo de proxy, combo de subtítulos, botón de tema y botón de programador; `grid_rowconfigure` actualizado a `row=5`

---

## 🗺️ Próximamente en v1.3.0

- Logging a archivo rotativo (`~/.novadl/novadl.log`)
- Verificación de integridad post-descarga
- Soporte multi-idioma de la interfaz (ES / EN)
- Atajos de teclado (Ctrl+V para pegar y escanear, Enter para descargar)

---

*Hecho con ❤️ por **DARK-CODE** — NovaDL es un proyecto personal. Si te es útil, dale una ⭐ al repo.*
