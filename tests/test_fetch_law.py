from ingest.fetch_law import chunk_articles, extract_text

# Mimics planalto's actual redline structure: an old <strike>d version, a middle
# version struck via inline CSS instead of a tag, and the current (unmarked) text.
SAMPLE_HTML = """
<html><body>
<p>SEÇÃO I</p>
<p>Da locação em geral</p>
<p><a name="art1"></a>Art. 1º Texto do artigo primeiro. </p>
<p>
<font><strike><a name="art2.."></a>Art. 2º Versão antiga revogada do artigo dois.</strike></font>
</p>
<p>
<span style="color:black; text-decoration:line-through">
<a name="art2"></a>Art. 2<u><sup>o</sup></u> Versão intermediária, também superada.
</span>
</p>
<p>
<a name="art2."></a>Art. 2<u><sup>o</sup></u> Versão atual e vigente do artigo dois.
</p>
<p>CAPÍTULO II</p>
<p>Das Ações de Despejo</p>
<p><a name="art3"></a>Art. 3º Texto do artigo três, no capítulo de despejo.</p>
<p>Brasília, 18 de outubro de 1991.</p>
<p>FERNANDO COLLOR</p>
</body></html>
"""


def test_strips_superseded_wording_and_keeps_current_version():
    text = extract_text(SAMPLE_HTML)
    chunks = chunk_articles(text)

    art2 = next(c for c in chunks if c["article_number"] == "2")
    assert "vigente" in art2["text"]
    assert "revogada" not in art2["text"]
    assert "superada" not in art2["text"]


def test_no_duplicate_article_numbers():
    text = extract_text(SAMPLE_HTML)
    chunks = chunk_articles(text)
    numbers = [c["article_number"] for c in chunks]
    assert len(numbers) == len(set(numbers))
    assert numbers == ["1", "2", "3"]


def test_chapter_metadata_tracks_nearest_heading():
    text = extract_text(SAMPLE_HTML)
    chunks = chunk_articles(text)

    art1 = next(c for c in chunks if c["article_number"] == "1")
    art3 = next(c for c in chunks if c["article_number"] == "3")
    assert art1["chapter"] is None or "locação em geral" in art1["chapter"]
    assert "Despejo" in art3["chapter"]


def test_trims_signature_block_from_last_article():
    text = extract_text(SAMPLE_HTML)
    chunks = chunk_articles(text)

    art3 = next(c for c in chunks if c["article_number"] == "3")
    assert "Brasília" not in art3["text"]
    assert "FERNANDO COLLOR" not in art3["text"]
