"""Email generator — random addresses from domains.txt."""

import random
import string
from pathlib import Path


class EmailGenerator:
    """Generate random email addresses from domain list."""

    def __init__(self, domains_file: str = "domains.txt"):
        self.domains_file = domains_file
        self.domains = []

    def __enter__(self):
        self.domains = self.load_domains(self.domains_file)
        return self

    def __exit__(self, *args):
        pass

    def load_domains(self, path: str) -> list[str]:
        """Load domains from file, one per line."""
        domains = []
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    domains.append(line)
        return domains

    def generate_email(self) -> str:
        """Generate random email: <random>@<random-domain>"""
        length = random.randint(8, 12)
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        domain = random.choice(self.domains)
        return f"{username}@{domain}"
