"""Contexto Cuentas (módulo `usuarios`).

Gestiona las **Cuentas** del sistema: usuario (estudiante o profesor),
establecimiento y administrador. «Usuario» y «Cuenta» no son sinónimos —
ver el lenguaje ubicuo en arc42 §8.1 y `docs/ddd-contextos.md` §1.

Es el único escritor de la entidad `Establecimiento` (ADR-0002). La
autenticación y los roles se implementarán en la próxima entrega.
"""
