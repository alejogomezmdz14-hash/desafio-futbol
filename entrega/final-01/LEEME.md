# Partido final (final-01)

Corrida del 13 de noviembre de 2026, de 11:10 a 11:47, contra la instancia del simulador que asignó la organización (acelerado ×3). El motor corrió en la notebook del equipo, sin juez automático. Cada pedido lo firmó el juez de turno por la API de la plataforma, la misma que usa la pantalla del juez, con el login de la coordinación.

| Archivo | Qué es |
|---|---|
| [`expediente.json`](expediente.json) | Primer expediente del partido (EXP-2026-000001), con su hash SHA-256 verificado |
| [`auditoria.jsonl`](auditoria.jsonl) | Registro de auditoría completo del partido: 141 eventos encadenados con hashes, cadena íntegra |

## Qué pasó, según nuestra auditoría
- **8 streams piratas detectados** y **2 descartados** (no eran la señal del partido o eran del licenciatario en su dominio).
- **8 pedidos firmados** por el juez de turno: 5 por la jueza Laura y 3 por el juez Martín. Cada uno se firmó en el mismo minuto de partido o al siguiente de la detección.
- **Cambio de turno en el minuto 50:** el juez Martín asumió el turno y ratificó las órdenes vigentes (`turno_asumido`).
- **32 órdenes enviadas y las 32 aplicadas** por los proveedores. Las 4 que el proveedor inestable hizo fallar se reenviaron solas y quedaron aplicadas.
- **Las 32 órdenes vencieron solas** al terminar el partido.
- **Ningún reclamo** de sitios legítimos.

El registro del simulador lo guarda la organización, que corre con él el verificador oficial. Por eso acá no está la salida de `evaluacion/verificar.py`.

## Cómo verificar la integridad
```bash
python -c "from plataforma.evidencia.gestor import GestorEvidencia; GestorEvidencia('entrega/final-01/auditoria.jsonl').verificar_integridad()"
```
