import bpy
from mathutils import Vector

# ==========================================
# НАСТРОЙКИ
# ==========================================

# Множитель размера (работает только на тех осях, где был сдвиг)
SCALE_FACTOR = 0.95

# Фактор сдвига рядов (0.0 - на месте, 1.0 - на краю)
SHIFT_FACTOR = 0.5

# Сброс формы перед изменениями
RESET_TO_UNIFORM = True 

# ==========================================

def process_lattice_smart_scale():
    selected_lattices = [o for o in bpy.context.selected_objects if o.type == 'LATTICE']
    
    if not selected_lattices:
        print("Не выделено ни одного объекта типа Lattice.")
        return

    bpy.context.view_layer.update()

    for obj in selected_lattices:
        lat = obj.data
        u_res = lat.points_u
        v_res = lat.points_v
        w_res = lat.points_w
        
        def get_idx(u, v, w):
            return w * (u_res * v_res) + v * u_res + u

        # --- ШАГ 1: СБРОС В РАВНОМЕРНУЮ СЕТКУ ---
        if RESET_TO_UNIFORM:
            for w in range(w_res):
                z_pos = -0.5 + (w / (w_res - 1)) if w_res > 1 else 0.0
                for v in range(v_res):
                    y_pos = -0.5 + (v / (v_res - 1)) if v_res > 1 else 0.0
                    for u in range(u_res):
                        x_pos = -0.5 + (u / (u_res - 1)) if u_res > 1 else 0.0
                        
                        idx = get_idx(u, v, w)
                        lat.points[idx].co_deform = Vector((x_pos, y_pos, z_pos))

        # --- ШАГ 2: СДВИГ ПРЕДПОСЛЕДНИХ РЯДОВ ---
        
        # Переменные-флаги, чтобы запомнить, где был сдвиг
        shifted_u = False
        shifted_v = False
        shifted_w = False

        # Ось U
        if u_res > 4:
            shifted_u = True
            for w in range(w_res):
                for v in range(v_res):
                    idx_0 = get_idx(0, v, w)
                    idx_1 = get_idx(1, v, w)
                    idx_last = get_idx(u_res - 1, v, w)
                    idx_pre  = get_idx(u_res - 2, v, w)
                    
                    p1 = lat.points[idx_1].co_deform
                    p0 = lat.points[idx_0].co_deform
                    lat.points[idx_1].co_deform = p1.lerp(p0, SHIFT_FACTOR)
                    
                    p_pre = lat.points[idx_pre].co_deform
                    p_last = lat.points[idx_last].co_deform
                    lat.points[idx_pre].co_deform = p_pre.lerp(p_last, SHIFT_FACTOR)

        # Ось V
        if v_res > 4:
            shifted_v = True
            for w in range(w_res):
                for u in range(u_res):
                    idx_0 = get_idx(u, 0, w)
                    idx_1 = get_idx(u, 1, w)
                    idx_last = get_idx(u, v_res - 1, w)
                    idx_pre  = get_idx(u, v_res - 2, w)
                    
                    p1 = lat.points[idx_1].co_deform
                    p0 = lat.points[idx_0].co_deform
                    lat.points[idx_1].co_deform = p1.lerp(p0, SHIFT_FACTOR)
                    
                    p_pre = lat.points[idx_pre].co_deform
                    p_last = lat.points[idx_last].co_deform
                    lat.points[idx_pre].co_deform = p_pre.lerp(p_last, SHIFT_FACTOR)

        # Ось W
        if w_res > 4:
            shifted_w = True
            for v in range(v_res):
                for u in range(u_res):
                    idx_0 = get_idx(u, v, 0)
                    idx_1 = get_idx(u, v, 1)
                    idx_last = get_idx(u, v, w_res - 1)
                    idx_pre  = get_idx(u, v, w_res - 2)
                    
                    p1 = lat.points[idx_1].co_deform
                    p0 = lat.points[idx_0].co_deform
                    lat.points[idx_1].co_deform = p1.lerp(p0, SHIFT_FACTOR)
                    
                    p_pre = lat.points[idx_pre].co_deform
                    p_last = lat.points[idx_last].co_deform
                    lat.points[idx_pre].co_deform = p_pre.lerp(p_last, SHIFT_FACTOR)

        # --- ШАГ 3: УМНЫЙ СКЕЙЛ (Только по активным осям) ---
        
        # Определяем множитель для каждой оси отдельно
        # Если ось сдвигалась (res > 4), применяем 0.95, иначе оставляем 1.0
        scale_u = SCALE_FACTOR if shifted_u else 1.0
        scale_v = SCALE_FACTOR if shifted_v else 1.0
        scale_w = SCALE_FACTOR if shifted_w else 1.0
        
        # Если хоть одна ось требует масштабирования
        if scale_u != 1.0 or scale_v != 1.0 or scale_w != 1.0:
            for point in lat.points:
                # Умножаем каждую компоненту вектора на свой множитель
                point.co_deform[0] *= scale_u # X
                point.co_deform[1] *= scale_v # Y
                point.co_deform[2] *= scale_w # Z

    print(f"Готово. Reset={RESET_TO_UNIFORM}, Shift={SHIFT_FACTOR}, Scale={SCALE_FACTOR} (Conditional)")

process_lattice_smart_scale()