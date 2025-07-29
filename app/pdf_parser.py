from dataclasses import dataclass
from agentic_doc.parse import parse 

@dataclass
class PdfParser:

    def __post_init__(self):
        pass

    def parse(self):
        result = parse("https://ogmmateryal.eba.gov.tr/panel/upload/files/y30nk0mh0s2.pdf")
        print(result[0].markdown)
        print(result[0].chunks)


if __name__ == "__main__":
    parser = PdfParser()
    parser.parse()