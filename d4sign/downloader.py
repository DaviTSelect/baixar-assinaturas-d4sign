from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Optional

import requests

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By

from .config import Config
from .models import Document
from .utils import is_pdf, sanitize_filename


class Downloader:
    """
    Downloader robusto para documentos do D4Sign.

    Estratégia:

    1. Aguarda a página carregar completamente.
    2. Aguarda a tabela/DOM estabilizar.
    3. Localiza os documentos usando find_elements.
    4. Faz scroll via JavaScript.
    5. Verifica cache/arquivo já existente.
    6. Tenta HTTP quando houver URL.
    7. Se HTTP falhar, usa Selenium.
    8. Aguarda o download terminar.
    9. Valida o PDF.
    10. Remove arquivos temporários/duplicados.
    11. Só depois o chamador deve avançar para a próxima página.
    """

    def __init__(
        self,
        config: Config,
        browser,
    ):
        self.config = config
        self.browser = browser
        self.session = requests.Session()

        self.debug_enabled = self._get_debug_flag()

        self.log("Downloader inicializado.")

    # =========================================================
    # DEBUG
    # =========================================================

    def _get_debug_flag(self) -> bool:
        """
        Tenta descobrir DEBUG de diferentes formas para evitar
        dependência rígida da implementação do Config.
        """

        try:
            value = getattr(self.config, "debug", False)

            if isinstance(value, bool):
                return value

            return str(value).strip().lower() in {
                "1",
                "true",
                "yes",
                "sim",
                "on",
            }

        except Exception:
            return False

    def log(self, message: str) -> None:
        print(f"[D4SIGN] {message}")

    def debug(self, message: str) -> None:
        if self.debug_enabled:
            print(f"[DEBUG] {message}")

    def debug_exception(
        self,
        message: str,
        exc: Exception,
    ) -> None:
        if self.debug_enabled:
            print(
                f"[DEBUG] {message}: "
                f"{type(exc).__name__}: {exc}"
            )

    # =========================================================
    # DRIVER
    # =========================================================

    @property
    def driver(self):
        return self.browser.current_driver

    # =========================================================
    # ESTADO DA PÁGINA
    # =========================================================

    def wait_document_ready(
        self,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Aguarda document.readyState = complete.

        Não depende exclusivamente disso para considerar a
        tabela carregada.
        """

        if timeout is None:
            timeout = 30

        self.debug(
            f"Aguardando document.readyState por até "
            f"{timeout}s..."
        )

        started = time.time()

        while time.time() - started < timeout:
            try:
                state = self.driver.execute_script(
                    "return document.readyState;"
                )

                self.debug(
                    f"document.readyState = {state}"
                )

                if state == "complete":
                    return True

            except WebDriverException as exc:
                self.debug_exception(
                    "Erro lendo readyState",
                    exc,
                )

            time.sleep(0.5)

        self.debug(
            "Timeout aguardando document.readyState."
        )

        return False

    # =========================================================
    # DEBUG DA PÁGINA
    # =========================================================

    def debug_page(self) -> None:
        """
        Mostra informações úteis do DOM quando DEBUG=true.
        """

        if not self.debug_enabled:
            return

        try:
            url = self.driver.current_url
        except Exception:
            url = "?"

        try:
            title = self.driver.title
        except Exception:
            title = "?"

        try:
            ready = self.driver.execute_script(
                "return document.readyState;"
            )
        except Exception:
            ready = "?"

        try:
            body_text = self.driver.execute_script(
                """
                return document.body
                    ? document.body.innerText
                    : '';
                """
            ) or ""

            body_preview = re.sub(
                r"\s+",
                " ",
                body_text,
            )[:1000]

        except Exception:
            body_preview = "ERRO"

        try:
            trs = self.driver.find_elements(
                By.CSS_SELECTOR,
                "tr",
            )
            tr_count = len(trs)
        except Exception:
            tr_count = -1

        self.debug(
            "================ ESTADO DA PÁGINA ================"
        )
        self.debug(f"URL: {url}")
        self.debug(f"TITLE: {title}")
        self.debug(f"READY: {ready}")
        self.debug(f"TRs: {tr_count}")
        self.debug(
            f"BODY: {body_preview}"
        )
        self.debug(
            "==================================================="
        )

    # =========================================================
    # SCROLL
    # =========================================================

    def scroll_page(self) -> None:
        """
        Faz scroll progressivo da página.

        Isso ajuda quando o D4Sign utiliza carregamento/renderização
        dependente da posição do elemento.
        """

        try:
            self.driver.execute_script(
                """
                window.scrollTo({
                    top: 0,
                    behavior: 'instant'
                });
                """
            )

            time.sleep(0.3)

            height = self.driver.execute_script(
                """
                return Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight
                );
                """
            )

            self.debug(
                f"Altura da página: {height}px"
            )

            positions = [
                0,
                300,
                700,
                1100,
                1600,
                height,
            ]

            for position in positions:
                try:
                    self.driver.execute_script(
                        """
                        window.scrollTo({
                            top: arguments[0],
                            behavior: 'instant'
                        });
                        """,
                        position,
                    )

                    time.sleep(0.25)

                except WebDriverException:
                    break

            self.driver.execute_script(
                """
                window.scrollTo({
                    top: 0,
                    behavior: 'instant'
                });
                """
            )

            time.sleep(0.5)

        except WebDriverException as exc:
            self.debug_exception(
                "Erro executando scroll",
                exc,
            )

    # =========================================================
    # LOCALIZAR LINHAS
    # =========================================================

    def find_document_rows(self):
        """
        Localiza as linhas de documentos.

        IMPORTANTE:
        Não utiliza apenas WebDriverWait.

        O D4Sign pode renderizar a tabela depois que a página
        já está readyState=complete.
        """

        selectors = [
            "table tbody tr",
            "tbody tr",
            "table tr",
            "tr",
        ]

        for selector in selectors:
            try:
                rows = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    selector,
                )

                self.debug(
                    f"Selector '{selector}' "
                    f"encontrou {len(rows)} elementos."
                )

                if rows:
                    return rows

            except WebDriverException as exc:
                self.debug_exception(
                    f"Erro no selector {selector}",
                    exc,
                )

        return []

    # =========================================================
    # AGUARDAR DOCUMENTOS
    # =========================================================

    def wait_for_documents(
        self,
        max_wait: int = 20,
        stable_checks: int = 3,
    ):
        """
        Aguarda a lista de documentos.

        Critério inteligente:

        - readyState complete;
        - procura TR;
        - faz scroll;
        - verifica várias vezes;
        - considera a quantidade estabilizada.

        Isso evita interpretar carregamento lento como
        página vazia.
        """

        self.log(
            "Aguardando documentos aparecerem..."
        )

        started = time.time()

        previous_count = None
        stable_count = 0

        attempt = 0

        while time.time() - started < max_wait:
            attempt += 1

            self.debug(
                f"Busca de documentos "
                f"tentativa {attempt}"
            )

            self.wait_document_ready(
                timeout=5
            )

            self.scroll_page()

            rows = self.find_document_rows()

            count = len(rows)

            self.debug(
                f"Quantidade atual de TRs: {count}"
            )

            # -------------------------------------------------
            # Encontrou documentos
            # -------------------------------------------------

            if count > 0:

                if count == previous_count:
                    stable_count += 1
                else:
                    stable_count = 0

                previous_count = count

                self.debug(
                    f"Quantidade estável: "
                    f"{stable_count}/{stable_checks}"
                )

                if stable_count >= stable_checks:
                    self.log(
                        f"Documentos encontrados: {count}"
                    )
                    return rows

            # -------------------------------------------------
            # Ainda vazio
            # -------------------------------------------------

            else:

                # Não encerramos imediatamente.
                # D4Sign pode ainda estar carregando.

                self.debug(
                    "Nenhum TR encontrado ainda."
                )

                self.debug_page()

            time.sleep(1)

        # =====================================================
        # TIMEOUT
        # =====================================================

        self.log(
            "Tempo máximo atingido aguardando documentos."
        )

        self.debug_page()

        return self.find_document_rows()

    # =========================================================
    # COOKIES
    # =========================================================

    def sync_cookies(self) -> None:
        """
        Copia cookies do Selenium para requests.
        """

        self.session.cookies.clear()

        try:
            cookies = self.driver.get_cookies()
        except WebDriverException as exc:
            self.debug_exception(
                "Erro obtendo cookies",
                exc,
            )
            return

        self.log(
            f"Sincronizando {len(cookies)} cookies..."
        )

        for cookie in cookies:
            try:
                self.session.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain"),
                    path=cookie.get("path", "/"),
                )

            except Exception as exc:
                self.debug_exception(
                    f"Erro copiando cookie "
                    f"{cookie.get('name')}",
                    exc,
                )

    # =========================================================
    # HEADERS
    # =========================================================

    def _headers(self) -> dict[str, str]:

        return {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "application/pdf,"
                "application/octet-stream,"
                "*/*"
            ),
            "Accept-Language": (
                "pt-BR,pt;q=0.9,"
                "en-US;q=0.8,en;q=0.7"
            ),
            "Referer": self.driver.current_url,
            "Connection": "keep-alive",
        }

    # =========================================================
    # URL
    # =========================================================

    def extract_download_url(
        self,
        row,
    ) -> Optional[str]:

        self.debug(
            "Procurando URL de download na linha..."
        )

        # -----------------------------------------------------
        # A
        # -----------------------------------------------------

        try:

            links = row.find_elements(
                By.CSS_SELECTOR,
                "a",
            )

            self.debug(
                f"Links encontrados na linha: "
                f"{len(links)}"
            )

            for link in links:

                try:

                    href = (
                        link.get_attribute("href")
                        or ""
                    ).strip()

                    text = (
                        link.text
                        or ""
                    ).strip()

                    onclick = (
                        link.get_attribute("onclick")
                        or ""
                    )

                    outer = (
                        link.get_attribute(
                            "outerHTML"
                        )
                        or ""
                    )

                    combined = (
                        href
                        + " "
                        + text
                        + " "
                        + onclick
                        + " "
                        + outer
                    ).lower()

                    if (
                        "download" in combined
                        or "baixar" in combined
                    ):
                        self.debug(
                            "Possível URL encontrada:"
                        )
                        self.debug(
                            f"href={href}"
                        )
                        self.debug(
                            f"text={text}"
                        )
                        self.debug(
                            f"onclick={onclick}"
                        )

                        if href:
                            return href

                except (
                    StaleElementReferenceException,
                    WebDriverException,
                ):
                    continue

        except WebDriverException as exc:

            self.debug_exception(
                "Erro procurando links",
                exc,
            )

        # -----------------------------------------------------
        # B
        # -----------------------------------------------------

        selectors = [
            "[href*='download']",
            "[href*='Download']",
            "[data-url*='download']",
            "[data-href*='download']",
            "[data-download]",
            "[onclick*='download']",
            "[onclick*='Download']",
            "[onclick*='baixar']",
            "[onclick*='Baixar']",
        ]

        for selector in selectors:

            try:

                elements = row.find_elements(
                    By.CSS_SELECTOR,
                    selector,
                )

                self.debug(
                    f"Selector {selector}: "
                    f"{len(elements)} elementos"
                )

                for element in elements:

                    for attr in (
                        "href",
                        "data-url",
                        "data-href",
                        "data-download",
                    ):

                        try:

                            value = (
                                element.get_attribute(
                                    attr
                                )
                                or ""
                            ).strip()

                            if value:
                                self.debug(
                                    f"{attr}={value}"
                                )

                            if value.startswith(
                                "http"
                            ):
                                return value

                        except (
                            StaleElementReferenceException,
                            WebDriverException,
                        ):
                            continue

            except WebDriverException:
                continue

        # -----------------------------------------------------
        # C - HTML
        # -----------------------------------------------------

        try:

            html = (
                row.get_attribute(
                    "outerHTML"
                )
                or ""
            )

            urls = re.findall(
                r"https?://[^\"']+",
                html,
            )

            self.debug(
                f"URLs encontradas no HTML: "
                f"{len(urls)}"
            )

            for url in urls:

                low = url.lower()

                if (
                    "download" in low
                    or "baixar" in low
                    or ".pdf" in low
                ):
                    return url

        except WebDriverException as exc:

            self.debug_exception(
                "Erro lendo HTML da linha",
                exc,
            )

        return None

    # =========================================================
    # BOTÃO
    # =========================================================

    def find_download_button(
        self,
        row,
    ):

        selectors = [

            (
                By.XPATH,
                ".//*[contains("
                "translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÇÃÕ',"
                "'abcdefghijklmnopqrstuvwxyzáéíóúçãõ'),"
                "'download (apenas assinaturas)'"
                ")]",
            ),

            (
                By.XPATH,
                ".//*[contains("
                "translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÇÃÕ',"
                "'abcdefghijklmnopqrstuvwxyzáéíóúçãõ'),"
                "'apenas assinaturas'"
                ")]",
            ),

            (
                By.XPATH,
                ".//*[contains("
                "translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÇÃÕ',"
                "'abcdefghijklmnopqrstuvwxyzáéíóúçãõ'),"
                "'download'"
                ")]",
            ),

            (
                By.XPATH,
                ".//*[contains("
                "translate(normalize-space(.), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÇÃÕ',"
                "'abcdefghijklmnopqrstuvwxyzáéíóúçãõ'),"
                "'baixar'"
                ")]",
            ),

            (
                By.CSS_SELECTOR,
                "[onclick*='download']",
            ),

            (
                By.CSS_SELECTOR,
                "[onclick*='Download']",
            ),

            (
                By.CSS_SELECTOR,
                "[onclick*='baixar']",
            ),

            (
                By.CSS_SELECTOR,
                "[onclick*='Baixar']",
            ),

            (
                By.CSS_SELECTOR,
                "a[download]",
            ),
        ]

        for by, selector in selectors:

            try:

                elements = row.find_elements(
                    by,
                    selector,
                )

                self.debug(
                    f"Botão selector={selector} "
                    f"quantidade={len(elements)}"
                )

                for element in elements:

                    try:

                        text = (
                            element.text
                            or ""
                        ).strip()

                        self.debug(
                            f"Elemento candidato: "
                            f"'{text}'"
                        )

                        if element.is_displayed():
                            return element

                    except (
                        StaleElementReferenceException,
                        WebDriverException,
                    ):
                        continue

            except WebDriverException:
                continue

        return None

    # =========================================================
    # DOWNLOAD HTTP
    # =========================================================

    def download_http(
        self,
        url: str,
        destination: Path,
    ) -> bool:

        self.log(
            "Tentando download HTTP..."
        )

        self.debug(
            f"URL HTTP: {url}"
        )

        self.sync_cookies()

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:

            response = self.session.get(
                url,
                headers=self._headers(),
                timeout=self.config.download_timeout,
                allow_redirects=True,
            )

            self.log(
                f"HTTP: {response.status_code}"
            )

            self.debug(
                f"Final URL: "
                f"{response.url}"
            )

            self.debug(
                f"Content-Type: "
                f"{response.headers.get('Content-Type')}"
            )

            self.debug(
                f"Tamanho: "
                f"{len(response.content)} bytes"
            )

            if response.status_code != 200:
                return False

            if response.content.startswith(
                b"%PDF-"
            ):

                destination.write_bytes(
                    response.content
                )

                if is_pdf(destination):

                    self.log(
                        "PDF baixado via HTTP."
                    )

                    return True

                destination.unlink(
                    missing_ok=True
                )

            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                )
                .lower()
            )

            if "text/html" in content_type:

                preview = (
                    response.text[:500]
                    .replace("\n", " ")
                    .replace("\r", " ")
                )

                self.debug(
                    "Servidor retornou HTML:"
                )

                self.debug(
                    preview
                )

        except requests.RequestException as exc:

            self.debug_exception(
                "Erro HTTP",
                exc,
            )

        except OSError as exc:

            self.debug_exception(
                "Erro salvando PDF",
                exc,
            )

        return False

    # =========================================================
    # ARQUIVOS
    # =========================================================

    def list_files(
        self,
        directory: Path,
    ) -> list[Path]:

        try:

            return [
                p
                for p in directory.iterdir()
                if p.is_file()
            ]

        except OSError as exc:

            self.debug_exception(
                "Erro listando arquivos",
                exc,
            )

            return []

    def cleanup_temporary_files(
        self,
        directory: Path,
    ) -> None:

        for path in self.list_files(directory):

            if path.name.endswith(
                ".crdownload"
            ):

                self.debug(
                    f"Download temporário encontrado: "
                    f"{path.name}"
                )

    # =========================================================
    # AGUARDAR DOWNLOAD
    # =========================================================

    def wait_for_download(
        self,
        download_dir: Path,
        before: set[str],
        timeout: Optional[int] = None,
    ) -> Optional[Path]:

        if timeout is None:
            timeout = self.config.download_timeout

        self.log(
            f"Aguardando conclusão do download "
            f"(até {timeout}s)..."
        )

        started = time.time()

        last_signature = None
        stable_seconds = 0

        while time.time() - started < timeout:

            time.sleep(1)

            files = self.list_files(
                download_dir
            )

            new_files = [
                p
                for p in files
                if p.name not in before
            ]

            self.debug(
                "Novos arquivos: "
                + str(
                    [
                        p.name
                        for p in new_files
                    ]
                )
            )

            # -------------------------------------------------
            # DOWNLOAD AINDA OCORRENDO
            # -------------------------------------------------

            temporary = [
                p
                for p in new_files
                if p.name.lower().endswith(
                    ".crdownload"
                )
            ]

            if temporary:

                self.debug(
                    "Ainda existem .crdownload."
                )

                continue

            # -------------------------------------------------
            # PDF
            # -------------------------------------------------

            pdfs = [
                p
                for p in new_files
                if p.suffix.lower() == ".pdf"
            ]

            if not pdfs:
                continue

            # -------------------------------------------------
            # VERIFICAR ESTABILIDADE DO TAMANHO
            # -------------------------------------------------

            signature = tuple(
                sorted(
                    (
                        p.name,
                        p.stat().st_size,
                    )
                    for p in pdfs
                )
            )

            if signature == last_signature:

                stable_seconds += 1

            else:

                stable_seconds = 0
                last_signature = signature

            self.debug(
                f"PDFs estáveis: "
                f"{stable_seconds}s"
            )

            if stable_seconds < 2:
                continue

            # -------------------------------------------------
            # PDF MAIS RECENTE
            # -------------------------------------------------

            pdf = max(
                pdfs,
                key=lambda p: p.stat().st_mtime,
            )

            self.debug(
                f"PDF detectado: {pdf.name}"
            )

            self.debug(
                f"Tamanho: "
                f"{pdf.stat().st_size} bytes"
            )

            if not is_pdf(pdf):

                self.debug(
                    "Arquivo encontrado "
                    "não é PDF válido."
                )

                continue

            return pdf

        self.log(
            "Timeout aguardando download."
        )

        return None

    # =========================================================
    # DOWNLOAD SELENIUM
    # =========================================================

    def download_selenium(
        self,
        row,
        destination: Path,
    ) -> bool:

        self.log(
            "Tentando download pelo Selenium..."
        )

        download_dir = (
            self.config.download_dir.resolve()
        )

        download_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # -----------------------------------------------------
        # Estado antes
        # -----------------------------------------------------

        before = {
            p.name
            for p in self.list_files(
                download_dir
            )
        }

        self.debug(
            f"Arquivos antes: "
            f"{len(before)}"
        )

        # -----------------------------------------------------
        # Procurar botão
        # -----------------------------------------------------

        button = self.find_download_button(
            row
        )

        if button is None:

            self.log(
                "Botão de download não encontrado."
            )

            if self.debug_enabled:

                try:

                    self.debug(
                        "HTML da linha:"
                    )

                    self.debug(
                        row.get_attribute(
                            "outerHTML"
                        )[:5000]
                    )

                except Exception:
                    pass

            return False

        # -----------------------------------------------------
        # Scroll
        # -----------------------------------------------------

        try:

            self.driver.execute_script(
                """
                arguments[0].scrollIntoView({
                    behavior: 'instant',
                    block: 'center',
                    inline: 'nearest'
                });
                """,
                button,
            )

            time.sleep(0.8)

        except WebDriverException as exc:

            self.debug_exception(
                "Erro no scroll do botão",
                exc,
            )

        # -----------------------------------------------------
        # Clique
        # -----------------------------------------------------

        clicked = False

        for attempt in range(1, 4):

            try:

                self.debug(
                    f"Tentativa de clique "
                    f"{attempt}/3"
                )

                # Revalidar posição
                self.driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                        behavior: 'instant',
                        block: 'center'
                    });
                    """,
                    button,
                )

                time.sleep(0.5)

                try:

                    button.click()

                except WebDriverException:

                    self.driver.execute_script(
                        "arguments[0].click();",
                        button,
                    )

                clicked = True
                break

            except (
                StaleElementReferenceException,
                WebDriverException,
            ) as exc:

                self.debug_exception(
                    "Falha no clique",
                    exc,
                )

                if attempt < 3:

                    time.sleep(1)

                    button = (
                        self.find_download_button(
                            row
                        )
                    )

                    if button is None:
                        break

        if not clicked:

            self.log(
                "Não foi possível clicar "
                "no botão de download."
            )

            return False

        self.log(
            "Clique realizado."
        )

        # -----------------------------------------------------
        # AGUARDAR
        # -----------------------------------------------------

        downloaded = self.wait_for_download(
            download_dir,
            before,
        )

        if downloaded is None:

            return False

        # -----------------------------------------------------
        # DESTINO
        # -----------------------------------------------------

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # -----------------------------------------------------
        # Se destino já existe
        # -----------------------------------------------------

        if destination.exists():

            if is_pdf(destination):

                self.debug(
                    "Destino já possui PDF válido."
                )

                try:
                    downloaded.unlink(
                        missing_ok=True
                    )
                except OSError:
                    pass

                return True

            else:

                self.debug(
                    "Destino existe, mas "
                    "não é PDF válido."
                )

                try:
                    destination.unlink(
                        missing_ok=True
                    )
                except OSError:
                    pass

        # -----------------------------------------------------
        # Mover
        # -----------------------------------------------------

        try:

            downloaded.replace(
                destination
            )

        except OSError as exc:

            self.debug_exception(
                "replace() falhou",
                exc,
            )

            try:

                destination.write_bytes(
                    downloaded.read_bytes()
                )

                downloaded.unlink(
                    missing_ok=True
                )

            except OSError as exc2:

                self.debug_exception(
                    "Falha copiando arquivo",
                    exc2,
                )

                return False

        # -----------------------------------------------------
        # VALIDAÇÃO FINAL
        # -----------------------------------------------------

        if not destination.exists():

            self.log(
                "Arquivo não apareceu no destino."
            )

            return False

        if not is_pdf(destination):

            self.log(
                "Arquivo final não é PDF válido."
            )

            try:
                destination.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

            return False

        self.log(
            f"PDF concluído: {destination.name}"
        )

        return True

    # =========================================================
    # DOCUMENTO
    # =========================================================

    def download_document(
        self,
        row,
        document: Document,
        destination: Path,
    ) -> bool:

        print()
        print(
            "=" * 70
        )
        print(
            f"Documento: {document.name}"
        )
        print(
            f"UUID: {document.uuid}"
        )
        print(
            f"Destino: {destination}"
        )
        print(
            "=" * 70
        )

        # -----------------------------------------------------
        # CACHE / DESTINO
        # -----------------------------------------------------

        if destination.exists():

            if is_pdf(destination):

                self.log(
                    "CACHE: arquivo já existe "
                    "e é PDF válido."
                )

                return True

            self.log(
                "Arquivo existente não é PDF válido."
            )

            try:
                destination.unlink(
                    missing_ok=True
                )
            except OSError:
                pass

        # -----------------------------------------------------
        # URL
        # -----------------------------------------------------

        url = document.download_url

        if not url:

            self.debug(
                "Document não possui download_url."
            )

            url = self.extract_download_url(
                row
            )

        # -----------------------------------------------------
        # HTTP
        # -----------------------------------------------------

        if url:

            retries = (
                self.config.download_retries
            )

            for attempt in range(
                1,
                retries + 1,
            ):

                self.log(
                    f"HTTP tentativa "
                    f"{attempt}/{retries}"
                )

                if self.download_http(
                    url,
                    destination,
                ):

                    return True

                if attempt < retries:

                    time.sleep(
                        self.config.retry_delay
                    )

        else:

            self.debug(
                "Nenhuma URL HTTP encontrada."
            )

        # -----------------------------------------------------
        # SELENIUM
        # -----------------------------------------------------

        self.log(
            "HTTP não conseguiu baixar."
        )

        self.log(
            "Fallback Selenium."
        )

        return self.download_selenium(
            row,
            destination,
        )

    # =========================================================
    # DESTINO
    # =========================================================

    def build_destination(
        self,
        folder_name: str,
        document_name: str,
    ) -> Path:

        folder = sanitize_filename(
            folder_name
        )

        filename = sanitize_filename(
            document_name
        )

        if not filename.lower().endswith(
            ".pdf"
        ):
            filename += ".pdf"

        return (
            self.config.download_dir
            / folder
            / filename
        )