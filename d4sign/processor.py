from __future__ import annotations

import time
from pathlib import Path

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .models import Statistics
from .parser import DocumentParser
from .utils import sanitize_filename, is_pdf


class Processor:

    def __init__(
        self,
        config,
        browser,
        downloader,
        cache,
    ):
        self.config = config
        self.browser = browser
        self.downloader = downloader
        self.cache = cache

    # =========================================================
    # PROCESSAR APENAS O LINK ESPECÍFICO
    # =========================================================

    def process_specific_link(self) -> Statistics:
        """
        Método adaptado para baixar arquivos exclusivamente do cofre específico
        passado pelo link: 1288308/e1334fa1-ccc7-4963-ae06-ec8ee1c93b62.html
        """
        stats = Statistics()

        # Extraindo o UUID diretamente do seu link
        project_id = "e1334fa1-ccc7-4963-ae06-ec8ee1c93b62"
        project_name = "Cofre_Especifico" 

        print()
        print("=" * 70)
        print("PROCESSANDO APENAS O COFRE ESPECÍFICO")
        print("=" * 70)
        print(f"Projeto: {project_name}")
        print(f"ID (Link): {project_id}")

        cached_count = len(
            self.cache.get_project(project_id)
        )

        print(
            f"UUIDs no cache: {cached_count}"
        )

        # =====================================================
        # DIRETÓRIO DO PROJETO (Onde os PDFs serão salvos)
        # =====================================================

        folder_dir = (
            self.config.download_dir
            / sanitize_filename(project_name)
        )

        folder_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # =====================================================
        # PAGINAÇÃO DO COFRE ESPECÍFICO
        # =====================================================

        page = 0

        while True:
            print()
            print("=" * 70)
            print(f"ABRINDO PÁGINA {page}")
            print("=" * 70)

            try:
                # Chama a navegação do Selenium passando apenas o UUID alvo
                rows = self.browser.open_folder_page(
                    project_id,
                    page,
                )

            except Exception as exc:
                print()
                print("✗ ERRO AO ABRIR PÁGINA")
                print(repr(exc))
                stats.errors += 1
                break

            # =================================================
            # NÃO HÁ MAIS DOCUMENTOS
            # =================================================

            if not rows:
                print()
                print(
                    f"Nenhum documento encontrado "
                    f"na página {page}."
                )
                break

            stats.pages += 1
            stats.documents += len(rows)

            print(
                f"Documentos encontrados na página: {len(rows)}"
            )

            # =================================================
            # DOCUMENTOS DA PÁGINA
            # =================================================

            for index, row in enumerate(
                rows,
                start=1,
            ):
                print()
                print("-" * 70)
                print(
                    f"DOCUMENTO {index}/{len(rows)}"
                )
                print("-" * 70)

                result = self.process_document(
                    row=row,
                    folder_dir=folder_dir,
                    project_id=project_id,
                )

                if result == "downloaded":
                    stats.downloaded += 1
                elif result == "cached":
                    stats.cached += 1
                elif result == "skipped":
                    stats.skipped += 1
                else:
                    stats.errors += 1

            # =================================================
            # PRÓXIMA PÁGINA
            # =================================================

            print()
            print("=" * 70)
            print(
                f"PÁGINA {page} CONCLUÍDA"
            )
            print("=" * 70)

            page += 1

        return stats

    # =========================================================
    # PROCESSAR DOCUMENTO
    # =========================================================

    def process_document(
        self,
        row,
        folder_dir: Path,
        project_id: str,
    ) -> str:

        uuid = DocumentParser.uuid(row)

        if not uuid:
            print("✗ UUID não encontrado.")
            return "error"

        uuid = str(uuid).strip()

        name = DocumentParser.name(row)
        if not name:
            name = "documento"

        name = str(name).strip()

        print(f"Nome: {name}")
        print(f"UUID: {uuid}")

        print("\nConsultando cache...")
        if self.cache.contains(project_id, uuid):
            print("✓ UUID encontrado no cache.")
            print("✓ Documento já foi baixado.")
            print("→ Pulando para o próximo.")
            return "cached"

        print("→ UUID não encontrado no cache.")
        print("→ Documento será analisado.")

        if not DocumentParser.finalized(row):
            print("\n→ Documento não está FINALIZADO.")
            print("→ Não será baixado.")
            return "skipped"

        print("\n✓ Documento está FINALIZADO.")

        filename = f"{sanitize_filename(name)} - {uuid}.pdf"
        destination = folder_dir / filename

        print(f"\nDestino:\n{destination}")

        if is_pdf(destination):
            print("\n✓ PDF já existe no disco.")
            print("→ Adicionando UUID ao cache.")
            self.cache.add(project_id, uuid)
            return "cached"

        print("\n" + "=" * 70)
        print("INICIANDO DOWNLOAD")
        print("=" * 70)

        success = self.download_selenium(
            row=row,
            destination=destination,
        )

        if success:
            print("\n✓ DOWNLOAD CONFIRMADO.")
            if is_pdf(destination):
                self.cache.add(project_id, uuid)
                print("\n✓ UUID adicionado ao cache.")
                return "downloaded"

            print("\n✗ Download retornou sucesso, mas o PDF não foi encontrado.")
            return "error"

        print("\n✗ DOWNLOAD FALHOU.")
        print("✗ UUID NÃO será colocado no cache.")
        return "error"

    # =========================================================
    # DOWNLOAD SELENIUM COM DELAY E CARREGAMENTO COMPLETO
    # =========================================================

    def download_selenium(
        self,
        row,
        destination: Path,
    ) -> bool:

        driver = self.browser.driver
        download_dir = Path(self.config.download_dir)
        
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            print(f"\n>>> Tentativa de download {attempt}/{max_retries}...")

            try:
                arquivos_antes = {
                    arquivo.resolve()
                    for arquivo in download_dir.glob("*")
                    if arquivo.is_file()
                }

                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                time.sleep(1)

                try:
                    menu_button = row.find_element(
                        By.CSS_SELECTOR,
                        "div.btn-group > i.dropdown-toggle, .dropdown-toggle, .fa-ellipsis-v, .fa-ellipsis-h"
                    )
                    driver.execute_script("arguments[0].click();", menu_button)
                    
                    print("✓ Menu de opções acionado. Aguardando carregamento dos elementos...")
                    time.sleep(2.0) 
                    
                except Exception as menu_exc:
                    print(f"⚠️ Aviso ao abrir menu (tentativa {attempt}): {menu_exc}")

                download_link = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//ul[contains(@class, 'dropdown-menu')]//a[contains(., 'Download (apenas assinaturas)') or contains(@href, '/pdf')]",
                        )
                    )
                )

                href_attr = download_link.get_attribute("href")

                if not href_attr or "javascript:" not in href_attr:
                    onclick_attr = download_link.get_attribute("onclick")
                    if onclick_attr:
                        href_attr = f"javascript: {onclick_attr}"

                print("✓ Link 'Download (apenas assinaturas)' capturado com sucesso.")

                if href_attr and href_attr.startswith("javascript:"):
                    js_code = href_attr.replace("javascript:", "").strip()
                    driver.execute_script(js_code)
                else:
                    driver.execute_script("arguments[0].click();", download_link)

                print("✓ Comando disparado. Aguardando arquivo PDF...")

                timeout = getattr(
                    self.config,
                    "download_timeout",
                    120,
                )

                inicio = time.time()
                arquivo_pdf = None
                ultimo_aviso = 0

                while time.time() - inicio < timeout:
                    tempo_decorrido = int(time.time() - inicio)
                    
                    if tempo_decorrido - ultimo_aviso >= 5:
                        print(f"...aguardando arquivo há {tempo_decorrido}s...")
                        ultimo_aviso = tempo_decorrido

                    arquivos = [
                        arquivo
                        for arquivo in download_dir.glob("*")
                        if arquivo.is_file()
                    ]

                    novos = [
                        arquivo
                        for arquivo in arquivos
                        if arquivo.resolve() not in arquivos_antes
                    ]

                    temporarios = [
                        arquivo
                        for arquivo in novos
                        if (
                            arquivo.name.endswith(".crdownload")
                            or arquivo.name.endswith(".tmp")
                            or arquivo.name.endswith(".part")
                        )
                    ]

                    if temporarios:
                        time.sleep(1)
                        continue

                    pdfs = [
                        arquivo
                        for arquivo in novos
                        if arquivo.suffix.lower() == ".pdf"
                    ]

                    if pdfs:
                        arquivo_pdf = max(
                            pdfs,
                            key=lambda arquivo: arquivo.stat().st_mtime,
                        )

                        tamanho_1 = arquivo_pdf.stat().st_size
                        time.sleep(1.5)

                        if not arquivo_pdf.exists():
                            continue

                        tamanho_2 = arquivo_pdf.stat().st_size

                        if tamanho_1 > 0 and tamanho_1 == tamanho_2:
                            break

                    time.sleep(1)

                if arquivo_pdf:
                    destination.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    if destination.exists():
                        try:
                            destination.unlink()
                        except OSError:
                            pass

                    arquivo_pdf.replace(destination)

                    if is_pdf(destination):
                        print("✓ DOWNLOAD CONCLUÍDO COM SUCESSO!")
                        return True

                print(f"⚠️ Tentativa {attempt} falhou: O arquivo PDF não apareceu a tempo.")

            except Exception as exc:
                print(f"⚠️ Erro na tentativa {attempt}: {repr(exc)}")

            time.sleep(3)

        print("\n✗ TIMEOUT / TODAS AS TENTATIVAS FALHARAM.")
        return False