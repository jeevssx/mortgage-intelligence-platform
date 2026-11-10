from src.ingestion.chunker import chunk_sections
from src.ingestion.loader import DocumentSection


def test_chunk_respects_size_and_overlap():
    words = [f"word{i}" for i in range(10)]
    section = DocumentSection(document_id="d.md", title="D", section="S", text=" ".join(words))

    chunks = chunk_sections([section], size_words=4, overlap_words=1)

    assert [c.text for c in chunks] == [
        "word0 word1 word2 word3",
        "word3 word4 word5 word6",
        "word6 word7 word8 word9",
    ]


def test_chunk_ids_are_sequential_and_unique_across_sections():
    s1 = DocumentSection(document_id="a.md", title="A", section="One", text="alpha beta gamma")
    s2 = DocumentSection(document_id="a.md", title="A", section="Two", text="delta epsilon zeta")

    chunks = chunk_sections([s1, s2], size_words=10, overlap_words=2)

    assert [c.chunk_id for c in chunks] == ["c-1", "c-2"]
    assert chunks[0].section == "One"
    assert chunks[1].section == "Two"


def test_chunk_overlap_must_be_smaller_than_size():
    section = DocumentSection(document_id="d.md", title="D", section="S", text="a b c")
    try:
        chunk_sections([section], size_words=4, overlap_words=4)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_empty_section_produces_no_chunks():
    section = DocumentSection(document_id="d.md", title="D", section="Empty", text="   ")
    assert chunk_sections([section], size_words=10, overlap_words=2) == []
