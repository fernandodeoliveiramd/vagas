"""
Testes de backend/app/database/db.py.

Cobre o escape do LIKE (find_existing_job/get_jobs) e a normalizacao de
URL - o bug original era: uma URL com underscore casava com qualquer
caractere no LIKE, tratando vagas diferentes como duplicatas e
descartando a mais nova em silencio.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import db as dbmod


class TestEscapeLike(unittest.TestCase):
    def test_escapa_underscore_e_porcentagem(self):
        self.assertEqual(dbmod.escape_like("vaga_do_ano%50"), "vaga\\_do\\_ano\\%50")

    def test_escapa_a_propria_barra_primeiro(self):
        # Se a barra de escape nao for escapada primeiro, um "\_" literal
        # no dado vira um escape acidental do proximo caractere.
        self.assertEqual(dbmod.escape_like("a\\_b"), "a\\\\\\_b")

    def test_string_sem_curinga_fica_igual(self):
        self.assertEqual(dbmod.escape_like("pelotas"), "pelotas")


class TestNormalizeUrl(unittest.TestCase):
    def test_remove_query_e_fragmento(self):
        self.assertEqual(
            dbmod.normalize_url("http://x.com/vaga?utm=1#topo"),
            "https://x.com/vaga"
        )

    def test_forca_https(self):
        self.assertEqual(dbmod.normalize_url("http://x.com/vaga"), "https://x.com/vaga")

    def test_remove_barra_final(self):
        self.assertEqual(dbmod.normalize_url("https://x.com/vaga/"), "https://x.com/vaga")


class TestFindExistingJobLikeEscape(unittest.TestCase):
    """
    Regressao do bug real: "vaga_1" e "vagaX1" sao URLs diferentes, mas
    sem escape o "_" de "vaga_1%" casava com o "X" de "vagaX1" no LIKE,
    fazendo insert_job() tratar a segunda como duplicata da primeira.
    """

    def setUp(self):
        self.tmpdb = tempfile.mktemp(suffix=".db")
        self._original_db_path = dbmod.DB_PATH
        dbmod.DB_PATH = self.tmpdb
        dbmod.init_db()

    def tearDown(self):
        dbmod.DB_PATH = self._original_db_path
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.tmpdb + suffix)
            except OSError:
                pass

    def test_underscore_na_url_nao_causa_falso_positivo(self):
        job_a = {"source": "Teste", "title": "Vaga A", "company": "Empresa A",
                  "location": "Pelotas", "url": "https://x.com/vaga_1"}
        job_b = {"source": "Teste", "title": "Vaga B", "company": "Empresa B",
                  "location": "Pelotas", "url": "https://x.com/vagaX1"}

        id_a = dbmod.insert_job(job_a)
        id_b = dbmod.insert_job(job_b)

        self.assertIsNotNone(id_a)
        self.assertIsNotNone(id_b)
        self.assertNotEqual(id_a, id_b)

    def test_mesma_url_e_deduplicada_de_verdade(self):
        job = {"source": "Teste", "title": "Vaga C", "company": "Empresa C",
                "location": "Pelotas", "url": "https://x.com/vaga_repetida"}

        id_primeira = dbmod.insert_job(dict(job))
        id_segunda = dbmod.insert_job(dict(job))

        self.assertIsNotNone(id_primeira)
        self.assertIsNone(id_segunda)  # duplicata real deve continuar sendo pulada


if __name__ == "__main__":
    unittest.main()
