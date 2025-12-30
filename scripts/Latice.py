import bpy
from mathutils import Vector, Matrix

def create_lattice_multi():
    # 1. Получаем список мешей из текущего выделения
    # Мы сохраняем список заранее, так как в процессе скрипта выделение будет меняться
    targets = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    
    if not targets:
        print("Не выбрано ни одного Mesh-объекта.")
        return

    # Обновляем граф сцены один раз перед стартом
    bpy.context.view_layer.update()
    
    # Список для сбора созданных латисов (чтобы потом их выделить)
    created_lattices = []

    # Снимаем выделение со всего, чтобы работать чисто
    bpy.ops.object.select_all(action='DESELECT')

    # --- НАЧАЛО ЦИКЛА ПО ОБЪЕКТАМ ---
    for obj in targets:
        try:
            # 2. Считаем Bounding Box (Local Space)
            bbox = [Vector(v) for v in obj.bound_box]
            min_v = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
            max_v = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
            
            local_center = (min_v + max_v) / 2
            local_size = max_v - min_v

            # 3. Определяем ориентацию (World X)
            rot_mat = obj.matrix_world.to_3x3().normalized()
            world_x = Vector((1, 0, 0))
            
            scores = [
                abs(rot_mat.col[0].dot(world_x)),
                abs(rot_mat.col[1].dot(world_x)),
                abs(rot_mat.col[2].dot(world_x))
            ]
            locked_idx = scores.index(max(scores))
            
            # 4. Расчет разрешения
            d_list = [local_size.x, local_size.y, local_size.z]
            resolutions = [2, 2, 2]
            
            active_dims = []
            for i in range(3):
                if i != locked_idx:
                    val = d_list[i] if d_list[i] > 0.0001 else 1.0
                    active_dims.append(val)
            
            min_dim = min(active_dims) if active_dims else 1.0
            
            for i in range(3):
                if i == locked_idx:
                    resolutions[i] = 2 # Ваше условие для оси X
                else:
                    dim = d_list[i] if d_list[i] > 0.0001 else 1.0
                    if abs(dim - min_dim) < 0.001:
                        resolutions[i] = 6
                    else:
                        ratio = dim / min_dim
                        target = ratio * 6
                        even_res = round(target / 2) * 2
                        resolutions[i] = int(max(2, even_res))

            # 5. Создаем Латис
            # Имя латиса делаем на основе имени объекта для порядка
            lat_name = f"Lattice_{obj.name}"
            lat_data = bpy.data.lattices.new(lat_name + "_Data")
            lat_obj = bpy.data.objects.new(lat_name, lat_data)
            
            lat_data.points_u = resolutions[0]
            lat_data.points_v = resolutions[1]
            lat_data.points_w = resolutions[2]
            
            lat_data.interpolation_type_u = 'KEY_BSPLINE'
            lat_data.interpolation_type_v = 'KEY_BSPLINE'
            lat_data.interpolation_type_w = 'KEY_BSPLINE'
            
            # Линкуем в ту же коллекцию, где лежит сам объект (или в активную)
            # Надежнее линковать в активную, чтобы было видно
            bpy.context.collection.objects.link(lat_obj)

            # 6. Позиционирование (Матрицы)
            mat_trans = Matrix.Translation(local_center)
            mat_scale = Matrix.Diagonal(local_size.to_4d())
            mat_scale[3][3] = 1.0 
            
            final_matrix = obj.matrix_world @ mat_trans @ mat_scale
            lat_obj.matrix_world = final_matrix

            # 7. Парентинг
            lat_obj.parent = obj
            lat_obj.matrix_parent_inverse = obj.matrix_world.inverted()

            # 8. Модификатор
            mod = obj.modifiers.new(name="AutoLattice", type='LATTICE')
            mod.object = lat_obj
            
            # Добавляем в список созданных
            created_lattices.append(lat_obj)
            
            print(f"Lattice created for {obj.name}")
            
        except Exception as e:
            print(f"Ошибка с объектом {obj.name}: {e}")

    # --- КОНЕЦ ЦИКЛА ---

    # В конце выделяем все созданные латисы
    for lat in created_lattices:
        lat.select_set(True)
    
    # Делаем последний созданный активным
    if created_lattices:
        bpy.context.view_layer.objects.active = created_lattices[-1]

# Запуск
create_lattice_multi()