from collections import defaultdict

class DataProcessor:

    def _as_monthly_rows(self, data_mensual):
        if isinstance(data_mensual, list):
            return data_mensual
        if isinstance(data_mensual, tuple):
            return list(data_mensual)
        return []

    def _row_get(self, row, key, index=None, default=None):
        if isinstance(row, dict):
            return row.get(key, default)
        if isinstance(row, (list, tuple)) and index is not None and len(row) > index:
            return row[index]
        return default
    
    def process_data(self, data_diaria, data_mensual):
        data_mensual = self._as_monthly_rows(data_mensual)

        if not data_diaria:
            # Si no hay datos del día, inicializamos todo en 0 o vacío
            por_pago_vacio = {}
            for row in data_mensual:
                descripcion = self._row_get(row, 'DESCRIPCION_PAGO', 0, '')
                if descripcion:
                    por_pago_vacio[descripcion] = 0
            return {
                'total_dia': 0,
                'por_pago': por_pago_vacio,
                'por_contado': {},
                'por_lista': {},
                'por_reparto': {},
                'facturas_count': 0,
                'promedio_factura': 0
            }

        total_dia = sum(float(row['total'] or 0) for row in data_diaria)

        facturas_unicas = set((row.get('CODIGO'), row.get('CLASE'), row.get('COMP')) for row in data_diaria)
        facturas_count = len(facturas_unicas)
        promedio_factura = total_dia / facturas_count if facturas_count > 0 else 0

        por_pago = defaultdict(float)
        por_contado = defaultdict(float)
        por_lista = defaultdict(float)
        por_reparto = defaultdict(float)

        for row in data_diaria:
            es_ticket = (row.get('CODIGO') == 'X') or (row.get('CLASE') == 'X')
            if not es_ticket:
                pago_desc = row['descripcion_pago'] or 'Sin definir'
                por_pago[pago_desc] += float(row['total'] or 0)
                
                tipo = 'Contado' if row['CONTADO'] == 'S' else 'Cuenta Corriente'
                por_contado[tipo] += float(row['total'] or 0)
            else:
                # Los tickets van por separado
                por_contado['TICKETS'] += float(row['total'] or 0)

            lista = row['LISTA'] or 'Sin asignar'
            por_lista[lista] += float(row['total'] or 0)

            reparto = row['REPARTO'].strip() if row['REPARTO'] else ''
            reparto_label = 'Retira' if reparto == 'N' else 'Reparto' if reparto == 'S' else reparto or 'No especificado'
            por_reparto[reparto_label] += float(row['total'] or 0)

        # Inicializar el dict final con valores del mes (incluso si el día no tiene venta)
        por_pago_final = {}
        por_reparto_final = {}
        por_contado_final = {'TICKETS': 0, 'Contado': 0, 'Cuenta Corriente': 0}

        # Mapear totales del mes y rellenar con 0 si no hubo ventas ese día
        for row in data_mensual:
            descripcion_pago = self._row_get(row, 'DESCRIPCION_PAGO', 0, '')
            total_mes = float(self._row_get(row, 'total', 2, 0) or 0)
            contado = self._row_get(row, 'CONTADO', 3, 'N')
            
            # TICKETS van por separado en el gráfico de contado
            if descripcion_pago == 'TICKET':
                por_contado_final['TICKETS'] += total_mes
            else:
                # Acumular por tipo (contado/cuenta corriente) - sin tickets
                tipo_pago = 'Contado' if contado == 'S' else 'Cuenta Corriente'
                por_contado_final[tipo_pago] += total_mes
                
                # Los tickets NO van a por_pago
                por_pago_final[descripcion_pago] = {
                    'total_dia': por_pago.get(descripcion_pago, 0),
                    'total_mes': por_pago_final.get(descripcion_pago, {}).get('total_mes', 0) + total_mes
                }
            
        for row in data_mensual:
            descripcion_pago = self._row_get(row, 'DESCRIPCION_PAGO', 0, '')
            reparto = self._row_get(row, 'REPARTO', 1, '')
            total_mes = float(self._row_get(row, 'total', 2, 0) or 0)
            # Excluir TICKET del reparto
            if descripcion_pago == 'TICKET':
                continue
            if reparto == 'S':
                reparto_label = 'Reparto'
            elif reparto == 'N':
                reparto_label = 'Retira'
            else:
                reparto_label = 'No especificado'
            por_reparto_final[reparto_label] = {
                'total_dia': por_reparto.get(reparto_label, 0),
                'total_mes': por_reparto_final.get(reparto_label, {}).get('total_mes', 0) + total_mes
            }
        
        # Convertir por_contado_final a estructura con total_dia/total_mes
        por_contado_result = {}
        for tipo in ['TICKETS', 'Contado', 'Cuenta Corriente']:
            por_contado_result[tipo] = {
                'total_dia': por_contado.get(tipo, 0),
                'total_mes': por_contado_final.get(tipo, 0)
            }

        return {
            'total_dia': total_dia,
            'por_pago': por_pago_final,
            'por_contado': por_contado_result,
            'por_lista': dict(por_lista),
            'por_reparto': por_reparto_final,
            'facturas_count': facturas_count,
            'promedio_factura': promedio_factura
        }