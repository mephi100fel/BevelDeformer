\# BevelDeformer

Аддон для Blender: создаёт lattice для выбранных мешей и даёт инструменты для деформации lattice.

## Структура проекта

- [addon/bevel_deformer](addon/bevel_deformer) — пакет аддона (это то, что ставится в Blender)
	- [addon/bevel_deformer/__init__.py](addon/bevel_deformer/__init__.py) — точка входа, регистрация, логотип в Preferences
	- [addon/bevel_deformer/lattice_ops.py](addon/bevel_deformer/lattice_ops.py) — создание/удаление lattice
	- [addon/bevel_deformer/deform_ops.py](addon/bevel_deformer/deform_ops.py) — деформация/сброс lattice
	- [addon/bevel_deformer/settings.py](addon/bevel_deformer/settings.py) — настройки (Scene properties)
	- [addon/bevel_deformer/ui.py](addon/bevel_deformer/ui.py) — панель View3D
	- [addon/bevel_deformer/icons](addon/bevel_deformer/icons) — ресурсы (логотип)
- [Legacy](Legacy) — старые однофайловые скрипты (не используются аддоном)

## Установка (через ZIP)

Важно: в корне ZIP должна лежать папка `bevel_deformer/`.

1) Открой папку [addon](addon)
2) Упакуй папку `bevel_deformer` в ZIP
3) Blender → Edit → Preferences → Add-ons → Install… → выбери ZIP → включи аддон

Проверка: внутри ZIP должно быть `bevel_deformer/__init__.py`, `bevel_deformer/ui.py`, `bevel_deformer/icons/logo.png`.

## Использование

Панель: View3D → Sidebar (N) → вкладка `Bevel` → `Bevel Deformer`.

### Lattice

- **Base Resolution** — базовая плотность по “активным” осям
- **World Axis** — выбор мирового направления, по которому выбирается “locked” ось (X/Y/Z)
- **Locked Axis Resolution** — плотность по locked оси
- **Interpolation** — тип интерполяции lattice
- **Create Lattice (Per Mesh)** — создаёт lattice для каждого выбранного меша (с подтверждением перезаписи)
- **Delete Lattice** — удаляет lattice (для выбранных мешей и/или выбранных lattice)

### Deform

- **Reset To Uniform** — сбрасывать точки lattice в равномерную сетку перед деформацией
- **Shift Factor** — насколько сдвигать “вторые ряды” к границам
- **Scale Factor** — масштабирование только по тем осям, где был shift
- **Deform Selected Lattices** — применить деформацию
- **Reset Selected Lattices** — сбросить в равномерную сетку

## Примечания и диагностика

- Если Blender открыл файл в read-only режиме (например, файл сохранён более новой версией Blender), регистрация UI может падать. Аддон ловит этот кейс и выводит подсказку. Обычно помогает `File → Save As…` в новый файл.
- После обновления аддона (замены файлов) часто достаточно Disable/Enable аддона в Preferences.


