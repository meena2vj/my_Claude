"""Fixed-length chunking of extracted PDF pages using LangChain's text splitter."""

from dataclasses import dataclass

try:
    from langchain_text_splitters import CharacterTextSplitter
except ImportError:  # older langchain versions bundle it under langchain.text_splitter
    from langchain.text_splitter import CharacterTextSplitter

from config import CHUNK_OVERLAP, CHUNK_SIZE
from src.ingestion.pdf_processor import PageRecord
from src.utils.helpers import count_tokens_approx


@dataclass
class ChunkRecord:
    chunk_id: str
    source_file: str
    page_number: int
    text: str
    token_count: int = 0
    is_suspicious: bool = False  # set by hybrid.guardrails.scan_chunks; never trust silently


def chunk_pages(
    pages: list[PageRecord],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[ChunkRecord]:
    """Split every non-empty page into fixed-length chunks.

    Splitting is done per page so each chunk keeps its source file and page
    number for citations.
    """
    splitter = CharacterTextSplitter(
        separator="",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks: list[ChunkRecord] = []
    next_id = 1
    for page in pages:
        if page.is_empty:
            continue
        for piece in splitter.split_text(page.page_text):
            if not piece.strip():
                continue
            chunks.append(
                ChunkRecord(
                    chunk_id=f"chunk_{next_id:05d}",
                    source_file=page.file_name,
                    page_number=page.page_number,
                    text=piece,
                    token_count=count_tokens_approx(piece),
                )
            )
            next_id += 1

    return chunks
