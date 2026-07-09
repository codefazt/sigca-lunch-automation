---
name: git_release
description: Guía y procesos detallados para compilar, empaquetar y publicar actualizaciones de SiGCABot en GitHub Releases usando la CLI 'gh'.
---

# 🚀 Proceso de Compilación y Publicación de Versiones (Releases)

Este documento define el procedimiento estándar para empaquetar y subir actualizaciones del SiGCABot a GitHub de forma que los bots locales instalados puedan auto-actualizarse en vivo.

## 📦 1. Compilación del Proyecto
Antes de generar el release, se debe compilar y empaquetar el binario físico utilizando el script de compilación del proyecto:

```powershell
# Compila, firma el ejecutable y empaqueta el release en dist\SiGCABot_Release.zip
.\build.bat --package
```

## 🔐 2. Autenticación en GitHub CLI (Si es necesario)
Para realizar acciones en GitHub por comandos, la sesión debe estar iniciada con los permisos del repositorio (usualmente la cuenta `codefazt`):

```powershell
# Cerrar sesión previa si choca de cuenta
gh auth logout

# Iniciar sesión fresca vía navegador
gh auth login -p https -w
```
*Asegúrate de conceder todos los permisos que solicite el navegador.*

## 🏷️ 3. Creación y Publicación del Release en GitHub
El actualizador del bot busca nuevas versiones consultando la API de releases. Para publicar la versión y adjuntar el binario compilado, ejecuta:

```powershell
gh release create <tag> <ruta_zip> --title "<titulo>" --notes "<notas>"
```

### Ejemplo de comando real:
```powershell
gh release create v2.4.0 dist\SiGCABot_Release.zip --title "Versión 2.4.0 - Actualizador Robusto" --notes "Incluye fixes de bloqueo de archivos y botón de búsqueda estático."
```

> [!IMPORTANT]
> * La etiqueta (tag) debe seguir el formato semántico `vX.Y.Z` (ejemplo: `v2.4.0`).
> * El archivo zip a subir debe ser exactamente `dist\SiGCABot_Release.zip` (que contiene el `.exe` y los scripts satélites libres de código fuente).
> * Los usuarios que tengan instalada una versión anterior (ejemplo: `2.3.0` o `2.2.0`) detectarán automáticamente la versión superior al consultar la API de GitHub.
