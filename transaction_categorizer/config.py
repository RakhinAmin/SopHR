# config.py
from dataclasses import dataclass

@dataclass
class Config:
    bank_statement_file: str
    rules_file: str
    output_file: str
    match_threshold: int = 70
    num_suggestions: int = 3
    auto_approve_threshold: int = 80
    chunk_size: int = 1000
    cache_size: int = 1000
