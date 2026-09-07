# Diagramas C4 — PideUTB

Diagramas del modelo C4 como código Mermaid, referenciados desde [`arc42.md`](../arc42/arc42.md) (secciones 3.2 y 5).

| Nivel | Archivo | Qué muestra |
|---|---|---|
| 1 — Contexto | [`nivel1-contexto.md`](nivel1-contexto.md) | PideUTB como caja negra: usuarios y sistemas externos (Wompi, Supabase). |
| 2 — Contenedores | [`nivel2-contenedores.md`](nivel2-contenedores.md) | Piezas desplegables: frontend web y API backend. |
| 3 — Módulos (caja blanca) | [`nivel3-modulos.md`](nivel3-modulos.md) | Módulos de dominio dentro de la API (`pedidos`, `menu`, `pagos`, `usuarios`) y sus reglas de comunicación (ADR-0001). |
