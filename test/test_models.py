from d4sign.models import Document, Folder, Statistics


def test_modelos_folder_e_document():
    folder = Folder(uuid="f1", name="Pasta")
    document = Document(uuid="d1", name="Doc", download_url="https://example.test/doc.pdf")
    assert (folder.uuid, folder.name) == ("f1", "Pasta")
    assert document.download_url.endswith(".pdf")


def test_statistics_add_soma_campos_exceto_folders():
    base = Statistics(folders=9, pages=1, documents=2, downloaded=3, cached=4, skipped=5, errors=6)
    other = Statistics(folders=10, pages=10, documents=20, downloaded=30, cached=40, skipped=50, errors=60)
    base.add(other)
    assert base.folders == 9
    assert (base.pages, base.documents, base.downloaded, base.cached, base.skipped, base.errors) == (
        11, 22, 33, 44, 55, 66
    )
