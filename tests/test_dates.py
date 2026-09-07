"""
Testes de backend/app/core/dates.py.

Este arquivo resolve datas relativas ("Ha 3 dias") em datas absolutas no
momento da captura. Sem isso, "Ha 3 dias" fica congelado no banco pra
sempre - o bug original que essa funcao corrige.
"""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.dates import parse_published_at


class TestParsePublishedAt(unittest.TestCase):
    def setUp(self):
        self.ref = datetime(2026, 9, 6, 12, 0, 0)

    def test_sem_data_util_retorna_none(self):
        for valor in ["Recente", "", None, "nao informado", "None", "null"]:
            with self.subTest(valor=valor):
                self.assertIsNone(parse_published_at(valor, self.ref))

    def test_ja_iso_e_normalizado(self):
        self.assertEqual(parse_published_at("2026-08-30T10:00:00", self.ref), "2026-08-30")
        self.assertEqual(parse_published_at("2026-08-30", self.ref), "2026-08-30")

    def test_hoje_e_ontem(self):
        self.assertEqual(parse_published_at("Hoje", self.ref), "2026-09-06")
        self.assertEqual(parse_published_at("Ontem", self.ref), "2026-09-05")

    def test_relativo_dias_e_semanas(self):
        self.assertEqual(parse_published_at("Há 3 dias", self.ref), "2026-09-03")
        self.assertEqual(parse_published_at("Há 1 semana", self.ref), "2026-08-30")
        self.assertEqual(parse_published_at("Há 3 semanas", self.ref), "2026-08-16")
        self.assertEqual(parse_published_at("há 2 meses", self.ref), "2026-07-08")

    def test_minutos_e_horas_nao_mudam_o_dia(self):
        # "Ha 2 horas" as 00h30 nao pode virar "ontem" so por causa da
        # aritmetica de subtrair horas cruzando a meia-noite.
        self.assertEqual(parse_published_at("Há 1 hora", self.ref), "2026-09-06")
        self.assertEqual(parse_published_at("Há 45 minutos", self.ref), "2026-09-06")

    def test_data_br_com_e_sem_ano(self):
        self.assertEqual(parse_published_at("Publicada em 15/06", self.ref), "2026-06-15")
        self.assertEqual(parse_published_at("19/06/2026", self.ref), "2026-06-19")

    def test_data_br_sem_ano_no_futuro_vira_ano_anterior(self):
        # Referencia em setembro/2026; "15/12" sem ano seria dezembro/2026,
        # no futuro em relacao a referencia - deve assumir 2025.
        self.assertEqual(parse_published_at("15/12", self.ref), "2025-12-15")

    def test_data_invalida_retorna_none(self):
        self.assertIsNone(parse_published_at("32/13/2026", self.ref))

    def test_idempotente_sobre_resultado_ja_processado(self):
        primeira = parse_published_at("Há 3 dias", self.ref)
        segunda = parse_published_at(primeira, self.ref)
        self.assertEqual(primeira, segunda)


if __name__ == "__main__":
    unittest.main()
