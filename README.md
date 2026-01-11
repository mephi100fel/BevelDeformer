# BevelDeformer

Аддон для Blender: создаёт lattice для выбранных мешей и даёт инструменты для деформации lattice.

Текущая версия: **v0.1.6** (Blender **4.5.0**).

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

Панель: View3D → Sidebar (N) → вкладка `Bevel_Deform` → `Bevel Deformer`.

Выделение поддерживается смешанное: можно выделять меши, lattice или оба типа одновременно.

### Lattice

- **Locked Axis** — включает режим лока одной оси. В этом режиме locked-ось всегда получает разрешение **2**.
- **Base Resolution** — базовая плотность по активным осям (адаптация под габариты сохраняется)
- **World Axis** — появляется только если `Locked Axis = True`. По этой мировой оси определяется, какая локальная ось lattice будет locked.
- **Interpolation** — тип интерполяции lattice
- **Create Lattice (Per Mesh)** — создаёт lattice для каждого выбранного меша (с подтверждением перезаписи)
- **Apply Interpolation to Selected** — применяет текущий тип интерполяции к выбранным lattice (или к lattice выбранных мешей)
- **Apply Lattice** — применяет lattice-модификатор и удаляет lattice (если больше не используется)
- **Delete Lattice** — удаляет lattice (для выбранных мешей и/или выбранных lattice)

Примечание: информация о locked-оси сохраняется внутри каждого созданного lattice через Custom Properties.

### Deform

- **Live Preview** — live-деформация при изменении ползунков (по умолчанию включено)
- **Reset To Uniform** — сбрасывать точки lattice в равномерную сетку перед деформацией
- **Shift Factor** — диапазон -1..1, управляет сдвигом с равномерным распределением (по умолчанию 0)
- **Scale Factor** — масштабирование по осям, где был shift (по умолчанию 1)
- **Offset X/Y/Z** — дополнительная деформация «размеров» по осям lattice с ramp-распределением
- **Deform Selected Lattices** — применить деформацию
- **Reset Selected Lattices** — сбросить в равномерную сетку + вернуть ползунки к дефолту (Scale=1, Shift=0, Offsets=0)

Если у конкретного lattice включён locked-axis, то оффсет по locked-оси не применяется (даже если ползунок двигается).

## Примечания и диагностика

- Если Blender открыл файл в read-only режиме (например, файл сохранён более новой версией Blender), регистрация UI может падать. Аддон ловит этот кейс и выводит подсказку. Обычно помогает `File → Save As…` в новый файл.
- После обновления аддона (замены файлов) часто достаточно Disable/Enable аддона в Preferences.


