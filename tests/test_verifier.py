"""
Testes de backend/app/services/verifier.py.

O verificador de links decide se uma vaga "acabou" procurando frases
como "vaga encerrada" no HTML. O bug original buscava na pagina inteira
(100KB), incluindo rodape/menu de portais grandes, o que apagava vagas
ativas por falso positivo. Agora a busca e restrita a <title>/<h1>.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.verifier import _extract_headline_text, CLOSED_PHRASES


class TestExtractHeadlineText(unittest.TestCase):
    def test_ignora_frase_de_encerramento_fora_do_titulo_e_h1(self):
        html = """<html><head><title>Vaga de Eletricista - Empresa X</title></head>
        <body><h1>Eletricista Industrial</h1>
        <footer>Veja tambem: <a href="#">vagas encerradas</a> do mes passado</footer>
        </body></html>"""
        headline = _extract_headline_text(html)
        for frase in CLOSED_PHRASES:
            self.assertNotIn(frase, headline, f"'{frase}' nao deveria vir do rodape")

    def test_detecta_frase_de_encerramento_no_titulo(self):
        html = '<html><head><title>Vaga Encerrada | Portal</title></head><body></body></html>'
        headline = _extract_headline_text(html)
        self.assertIn("vaga encerrada", headline)

    def test_detecta_frase_de_encerramento_no_h1(self):
        html = '<html><body><h1>Processo Seletivo Encerrado</h1></body></html>'
        headline = _extract_headline_text(html)
        self.assertIn("processo seletivo encerrado", headline)

    def test_html_sem_title_nem_h1_retorna_vazio(self):
        html = '<html><body><p>Descricao qualquer da vaga</p></body></html>'
        self.assertEqual(_extract_headline_text(html), "")

    def test_remove_tags_internas_do_title(self):
        html = '<html><head><title>Vaga <b>Encerrada</b></title></head></html>'
        headline = _extract_headline_text(html)
        self.assertIn("vaga", headline)
        self.assertIn("encerrada", headline)
        self.assertNotIn("<b>", headline)


if __name__ == "__main__":
    unittest.main()
