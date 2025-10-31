"""
Sistema Académico Automático por Fechas
Determina automáticamente semestre y corte basándome en el mes actual
"""

import psycopg2
from datetime import datetime, date
import calendar

# Configuración de la base de datos
DATABASE_CONFIG = {
    'host': 'localhost',
    'database': 'prototipoPG_v2',
    'user': 'postgres',
    'password': 'camilomena',
    'port': '5432'
}

class GestorAcademicoAutomatico:
    """
    Gestiona automáticamente la lógica académica basándose en fechas
    """
    
    def __init__(self):
        # CONFIGURACIÓN DEL AÑO ACADÉMICO
        # Puedes modificar estos rangos según tu institución
        
        self.configuracion_academica = {
            # PRIMER SEMESTRE (Enero - Junio)
            '2025-1': {
                'meses': [1, 2, 3, 4, 5, 6],  # Enero a Junio
                'cortes': {
                    1: [1, 2],      # Corte 1: Enero-Febrero  
                    2: [3, 4],      # Corte 2: Marzo-Abril
                    3: [5, 6]       # Corte 3: Mayo-Junio
                }
            },
            
            # SEGUNDO SEMESTRE (Julio - Diciembre)
            '2025-2': {
                'meses': [7, 8, 9, 10, 11, 12],  # Julio a Diciembre
                'cortes': {
                    1: [7, 8],      # Corte 1: Julio-Agosto
                    2: [9, 10],     # Corte 2: Septiembre-Octubre  
                    3: [11, 12]     # Corte 3: Noviembre-Diciembre
                }
            }
        }
    
    def obtener_fecha_actual(self):
        """Obtiene la fecha actual del sistema"""
        return datetime.now()
    
    def determinar_semestre_actual(self, fecha=None):
        """
        Determina el semestre actual basándome en el mes
        
        Args:
            fecha: Fecha específica (opcional, usa fecha actual si no se proporciona)
            
        Returns:
            tuple: (año, semestre) ejemplo: (2025, '2025-1')
        """
        if fecha is None:
            fecha = self.obtener_fecha_actual()
        
        año = fecha.year
        mes = fecha.month
        
        # Determinar semestre basándome en el mes
        if mes in [1, 2, 3, 4, 5, 6]:
            semestre = f"{año}-1"
        else:  # meses 7, 8, 9, 10, 11, 12
            semestre = f"{año}-2"
        
        return año, semestre
    
    def determinar_corte_actual(self, fecha=None):
        """
        Determina el corte actual basándome en el mes
        
        Args:
            fecha: Fecha específica (opcional)
            
        Returns:
            tuple: (año, semestre, corte) ejemplo: (2025, '2025-1', 2)
        """
        if fecha is None:
            fecha = self.obtener_fecha_actual()
        
        año, semestre = self.determinar_semestre_actual(fecha)
        mes = fecha.month
        
        # Buscar en qué corte está el mes actual
        config_semestre = self.configuracion_academica[semestre]
        
        for corte_num, meses_corte in config_semestre['cortes'].items():
            if mes in meses_corte:
                return año, semestre, corte_num
        
        # Si no encuentra, devolver el primer corte del semestre
        return año, semestre, 1
    
    def obtener_info_academica_completa(self, fecha=None):
        """
        Obtiene toda la información académica para una fecha
        
        Returns:
            dict: Información completa del contexto académico actual
        """
        if fecha is None:
            fecha = self.obtener_fecha_actual()
        
        año, semestre, corte = self.determinar_corte_actual(fecha)
        
        info = {
            'fecha_consultada': fecha.strftime('%Y-%m-%d %H:%M:%S'),
            'año': año,
            'semestre': semestre,
            'corte': corte,
            'mes_actual': fecha.month,
            'nombre_mes': calendar.month_name[fecha.month],
            'descripcion_periodo': f"Año {año}, {semestre}, Corte {corte}",
            'es_primer_semestre': semestre.endswith('-1'),
            'es_segundo_semestre': semestre.endswith('-2')
        }
        
        return info
    
    def conectar_bd(self):
        """Conectar a la base de datos"""
        try:
            conn = psycopg2.connect(**DATABASE_CONFIG)
            return conn
        except Exception as e:
            print(f"❌ Error conectando a BD: {e}")
            return None
    
    def obtener_sesion_activa_actual(self):
        """
        Busca la sesión que debería estar activa ahora mismo
        basándose en fecha y hora actual
        
        Returns:
            dict: Información de la sesión activa o None
        """
        conn = self.conectar_bd()
        if not conn:
            return None
        
        try:
            fecha_actual = datetime.now()
            año, semestre, corte = self.determinar_corte_actual(fecha_actual)
            
            # Buscar sesión programada para hoy en el corte actual
            query = """
            SELECT 
                id_sesion,
                nombre_sesion,
                descripcion,
                fecha_programada,
                hora_inicio,
                hora_fin,
                aula,
                estado,
                asistencia_habilitada
            FROM sesiones_academicas 
            WHERE fecha_programada = %s
            AND año = %s 
            AND semestre = %s 
            AND corte = %s
            AND hora_inicio <= %s 
            AND hora_fin >= %s
            LIMIT 1;
            """
            
            cursor = conn.cursor()
            cursor.execute(query, (
                fecha_actual.date(),
                año,
                semestre, 
                corte,
                fecha_actual.time(),
                fecha_actual.time()
            ))
            
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return {
                    'id_sesion': resultado[0],
                    'nombre_sesion': resultado[1],
                    'descripcion': resultado[2],
                    'fecha_programada': resultado[3],
                    'hora_inicio': resultado[4],
                    'hora_fin': resultado[5],
                    'aula': resultado[6],
                    'estado': resultado[7],
                    'asistencia_habilitada': resultado[8],
                    'contexto_academico': self.obtener_info_academica_completa()
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error buscando sesión activa: {e}")
            return None
        finally:
            conn.close()
    
    def habilitar_asistencia_automatica(self):
        """
        Habilita automáticamente la asistencia para la sesión actual
        si hay una sesión programada para este momento
        
        Returns:
            dict: Resultado de la operación
        """
        sesion_actual = self.obtener_sesion_activa_actual()
        
        if not sesion_actual:
            return {
                'exito': False,
                'mensaje': 'No hay sesión programada para este momento',
                'contexto_academico': self.obtener_info_academica_completa()
            }
        
        conn = self.conectar_bd()
        if not conn:
            return {'exito': False, 'mensaje': 'Error de conexión a BD'}
        
        try:
            # Habilitar asistencia para la sesión
            query = """
            UPDATE sesiones_academicas 
            SET asistencia_habilitada = true,
                estado = 'activa',
                actualizada_en = CURRENT_TIMESTAMP
            WHERE id_sesion = %s;
            """
            
            cursor = conn.cursor()
            cursor.execute(query, (sesion_actual['id_sesion'],))
            conn.commit()
            cursor.close()
            
            return {
                'exito': True,
                'mensaje': f"Asistencia habilitada para: {sesion_actual['nombre_sesion']}",
                'sesion': sesion_actual,
                'id_sesion_activa': sesion_actual['id_sesion']
            }
            
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Error habilitando asistencia: {e}'
            }
        finally:
            conn.close()
    
    def registrar_asistencia_automatica(self, id_estudiante, metodo='reconocimiento_facial', confidence_score=None):
        """
        Registra automáticamente asistencia en la sesión actual activa
        
        Args:
            id_estudiante: ID del estudiante
            metodo: Método de registro
            confidence_score: Puntuación de confianza
            
        Returns:
            dict: Resultado del registro
        """
        # Buscar sesión activa actual
        sesion_actual = self.obtener_sesion_activa_actual()
        
        if not sesion_actual:
            return {
                'exito': False,
                'mensaje': 'No hay sesión activa para registrar asistencia',
                'contexto_academico': self.obtener_info_academica_completa()
            }
        
        if not sesion_actual['asistencia_habilitada']:
            return {
                'exito': False,
                'mensaje': 'La asistencia no está habilitada para esta sesión',
                'sesion': sesion_actual['nombre_sesion']
            }
        
        conn = self.conectar_bd()
        if not conn:
            return {'exito': False, 'mensaje': 'Error de conexión a BD'}
        
        try:
            # Verificar si ya existe asistencia
            verificar_query = """
            SELECT id_asistencia, estado 
            FROM asistencias_academicas 
            WHERE id_sesion = %s AND id_estudiante = %s;
            """
            
            cursor = conn.cursor()
            cursor.execute(verificar_query, (sesion_actual['id_sesion'], id_estudiante))
            asistencia_existente = cursor.fetchone()
            
            if asistencia_existente:
                return {
                    'exito': False,
                    'mensaje': f'Asistencia ya registrada como: {asistencia_existente[1]}',
                    'estado_actual': asistencia_existente[1]
                }
            
            # Calcular estado y tardanza
            ahora = datetime.now()
            hora_inicio_sesion = datetime.combine(ahora.date(), sesion_actual['hora_inicio'])
            tolerancia = 15  # minutos de tolerancia
            
            diferencia_minutos = (ahora - hora_inicio_sesion).total_seconds() / 60
            
            if diferencia_minutos <= tolerancia:
                estado = 'presente'
                minutos_tardanza = 0
            else:
                estado = 'tardanza'
                minutos_tardanza = int(diferencia_minutos)
            
            # Registrar asistencia
            insertar_query = """
            INSERT INTO asistencias_academicas (
                id_sesion, id_estudiante, fecha_registro, metodo_registro,
                confidence_score, estado, minutos_tardanza
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_asistencia;
            """
            
            cursor.execute(insertar_query, (
                sesion_actual['id_sesion'],
                id_estudiante,
                ahora,
                metodo,
                confidence_score,
                estado,
                minutos_tardanza
            ))
            
            id_asistencia = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            return {
                'exito': True,
                'mensaje': f'Asistencia registrada como: {estado}',
                'id_asistencia': id_asistencia,
                'estado': estado,
                'minutos_tardanza': minutos_tardanza,
                'sesion': sesion_actual['nombre_sesion'],
                'contexto_academico': sesion_actual['contexto_academico']
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'exito': False,
                'mensaje': f'Error registrando asistencia: {e}'
            }
        finally:
            conn.close()
    
    def obtener_estadisticas_corte_actual(self):
        """
        Obtiene estadísticas del corte académico actual
        
        Returns:
            dict: Estadísticas del corte actual
        """
        año, semestre, corte = self.determinar_corte_actual()
        
        conn = self.conectar_bd()
        if not conn:
            return None
        
        try:
            # Estadísticas de sesiones
            query_sesiones = """
            SELECT 
                COUNT(*) as total_sesiones,
                COUNT(CASE WHEN estado = 'finalizada' THEN 1 END) as sesiones_completadas,
                COUNT(CASE WHEN estado = 'activa' THEN 1 END) as sesiones_activas,
                COUNT(CASE WHEN estado = 'programada' THEN 1 END) as sesiones_pendientes
            FROM sesiones_academicas
            WHERE año = %s AND semestre = %s AND corte = %s;
            """
            
            cursor = conn.cursor()
            cursor.execute(query_sesiones, (año, semestre, corte))
            stats_sesiones = cursor.fetchone()
            
            # Estadísticas de asistencias
            query_asistencias = """
            SELECT 
                COUNT(*) as total_asistencias,
                COUNT(CASE WHEN aa.estado = 'presente' THEN 1 END) as asistencias_puntuales,
                COUNT(CASE WHEN aa.estado = 'tardanza' THEN 1 END) as asistencias_tardias,
                COUNT(CASE WHEN aa.estado = 'ausente' THEN 1 END) as ausencias,
                AVG(aa.minutos_tardanza) as promedio_tardanza
            FROM asistencias_academicas aa
            JOIN sesiones_academicas sa ON aa.id_sesion = sa.id_sesion
            WHERE sa.año = %s AND sa.semestre = %s AND sa.corte = %s;
            """
            
            cursor.execute(query_asistencias, (año, semestre, corte))
            stats_asistencias = cursor.fetchone()
            
            cursor.close()
            
            return {
                'contexto_academico': self.obtener_info_academica_completa(),
                'sesiones': {
                    'total': stats_sesiones[0],
                    'completadas': stats_sesiones[1],
                    'activas': stats_sesiones[2], 
                    'pendientes': stats_sesiones[3]
                },
                'asistencias': {
                    'total': stats_asistencias[0] or 0,
                    'puntuales': stats_asistencias[1] or 0,
                    'tardias': stats_asistencias[2] or 0,
                    'ausencias': stats_asistencias[3] or 0,
                    'promedio_tardanza': float(stats_asistencias[4] or 0)
                }
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            return None
        finally:
            conn.close()

def mostrar_informacion_actual():
    """Función de prueba para mostrar información actual"""
    gestor = GestorAcademicoAutomatico()
    
    print("🎓 INFORMACIÓN ACADÉMICA ACTUAL")
    print("="*60)
    
    # Información básica
    info = gestor.obtener_info_academica_completa()
    print(f"📅 Fecha: {info['fecha_consultada']}")
    print(f"📚 Período: {info['descripcion_periodo']}")
    print(f"🗓️ Mes: {info['nombre_mes']} (mes {info['mes_actual']})")
    
    # Sesión activa
    print(f"\n🎯 SESIÓN ACTUAL:")
    print("-"*40)
    sesion = gestor.obtener_sesion_activa_actual()
    if sesion:
        print(f"✅ Sesión activa: {sesion['nombre_sesion']}")
        print(f"🕐 Horario: {sesion['hora_inicio']} - {sesion['hora_fin']}")
        print(f"📍 Aula: {sesion['aula']}")
        print(f"🎛️ Asistencia habilitada: {sesion['asistencia_habilitada']}")
    else:
        print("❌ No hay sesión activa en este momento")
    
    # Estadísticas
    print(f"\n📊 ESTADÍSTICAS DEL CORTE ACTUAL:")
    print("-"*40)
    stats = gestor.obtener_estadisticas_corte_actual()
    if stats:
        print(f"📋 Sesiones: {stats['sesiones']['completadas']}/{stats['sesiones']['total']} completadas")
        print(f"👥 Asistencias: {stats['asistencias']['total']} registros")
        print(f"⏰ Tardanzas: {stats['asistencias']['tardias']} ({stats['asistencias']['promedio_tardanza']:.1f} min promedio)")

if __name__ == "__main__":
    mostrar_informacion_actual()