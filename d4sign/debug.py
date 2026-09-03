from pathlib import Path
from datetime import datetime
import json
import time


class Debugger:

    def __init__(
        self,
        driver,
        enabled=True,
        save_screenshots=True,
        save_html=True,
        save_text=True,
        directory="debug",
    ):
        self.driver = driver
        self.enabled = enabled

        self.save_screenshots = save_screenshots
        self.save_html = save_html
        self.save_text = save_text

        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def log(self, message):
        if not self.enabled:
            return

        print(f"[DEBUG] {message}")

    def separator(self, title=""):
        if not self.enabled:
            return

        print()
        print("=" * 80)

        if title:
            print(f"[DEBUG] {title}")

        print("=" * 80)

    def page_info(self):
        if not self.enabled:
            return

        try:
            ready_state = self.driver.execute_script(
                "return document.readyState;"
            )

            url = self.driver.current_url

            title = self.driver.title

            html_size = len(
                self.driver.page_source or ""
            )

            body_text = self.driver.execute_script(
                """
                return document.body
                    ? document.body.innerText
                    : '';
                """
            )

            print(f"[DEBUG] URL: {url}")
            print(f"[DEBUG] TITLE: {title}")
            print(f"[DEBUG] READY STATE: {ready_state}")
            print(f"[DEBUG] HTML SIZE: {html_size}")
            print(
                f"[DEBUG] BODY TEXT SIZE: "
                f"{len(body_text)}"
            )

        except Exception as e:
            print(
                f"[DEBUG] Erro obtendo informações "
                f"da página: {e}"
            )

    def inspect_dom(self):
        if not self.enabled:
            return

        try:
            result = self.driver.execute_script(
                """
                return {
                    readyState: document.readyState,

                    trs: document.querySelectorAll(
                        'tr'
                    ).length,

                    links: document.querySelectorAll(
                        'a'
                    ).length,

                    buttons: document.querySelectorAll(
                        'button'
                    ).length,

                    inputs: document.querySelectorAll(
                        'input'
                    ).length,

                    divs: document.querySelectorAll(
                        'div'
                    ).length,

                    bodyText: document.body
                        ? document.body.innerText
                        : ''
                };
                """
            )

            print(
                f"[DEBUG] TR: "
                f"{result.get('trs')}"
            )

            print(
                f"[DEBUG] A: "
                f"{result.get('links')}"
            )

            print(
                f"[DEBUG] BUTTON: "
                f"{result.get('buttons')}"
            )

            print(
                f"[DEBUG] INPUT: "
                f"{result.get('inputs')}"
            )

            print(
                f"[DEBUG] DIV: "
                f"{result.get('divs')}"
            )

            text = result.get("bodyText", "")

            print(
                "[DEBUG] Primeiros 2000 caracteres "
                "do BODY:"
            )

            print(text[:2000])

        except Exception as e:
            print(
                f"[DEBUG] Erro analisando DOM: {e}"
            )

    def save_state(self, name):
        if not self.enabled:
            return

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        safe_name = "".join(
            c if c.isalnum() or c in "_-"
            else "_"
            for c in name
        )

        prefix = (
            self.directory
            / f"{timestamp}_{safe_name}"
        )

        try:
            if self.save_screenshots:
                self.driver.save_screenshot(
                    str(prefix.with_suffix(".png"))
                )

            if self.save_html:
                html = self.driver.page_source

                prefix.with_suffix(
                    ".html"
                ).write_text(
                    html,
                    encoding="utf-8",
                )

            if self.save_text:
                text = self.driver.execute_script(
                    """
                    return document.body
                        ? document.body.innerText
                        : '';
                    """
                )

                prefix.with_suffix(
                    ".txt"
                ).write_text(
                    text,
                    encoding="utf-8",
                )

            self.log(
                f"Estado salvo em: {prefix}"
            )

        except Exception as e:
            self.log(
                f"Erro salvando estado: {e}"
            )

    def inspect_elements(
        self,
        selector,
        description=None,
    ):
        if not self.enabled:
            return []

        description = (
            description or selector
        )

        try:
            elements = self.driver.find_elements(
                "css selector",
                selector,
            )

            print(
                f"[DEBUG] "
                f"{description}: "
                f"{len(elements)} elemento(s)"
            )

            for index, element in enumerate(
                elements[:20]
            ):
                try:
                    print(
                        f"[DEBUG]   "
                        f"[{index}] "
                        f"displayed="
                        f"{element.is_displayed()} "
                        f"enabled="
                        f"{element.is_enabled()} "
                        f"text="
                        f"{element.text[:200]!r}"
                    )

                except Exception as e:
                    print(
                        f"[DEBUG]   "
                        f"[{index}] erro: {e}"
                    )

            return elements

        except Exception as e:
            print(
                f"[DEBUG] Erro procurando "
                f"{description}: {e}"
            )

            return []

    def scroll_to(self, element):
        if not self.enabled:
            return

        try:
            self.driver.execute_script(
                """
                arguments[0].scrollIntoView({
                    behavior: 'instant',
                    block: 'center',
                    inline: 'center'
                });
                """,
                element,
            )

            time.sleep(0.5)

            self.log(
                "Elemento rolado para o centro da tela."
            )

        except Exception as e:
            self.log(
                f"Erro fazendo scroll: {e}"
            )