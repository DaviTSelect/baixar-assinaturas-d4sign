from typing import Optional

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

from .utils import extract_uuid


class DocumentParser:

    @staticmethod
    def uuid(row) -> Optional[str]:

        selectors = [
            "input.chevmov",
            "input[type='checkbox']",
            "[id^='nome_documento_']",
        ]

        for selector in selectors:

            try:

                elements = row.find_elements(
                    By.CSS_SELECTOR,
                    selector,
                )

                for element in elements:

                    for attr in (
                        "value",
                        "id",
                        "data-id",
                        "data-uuid",
                    ):

                        value = (
                            element.get_attribute(attr)
                            or ""
                        )

                        uuid = extract_uuid(value)

                        if uuid:
                            return uuid

            except WebDriverException:
                continue

        try:

            html = row.get_attribute(
                "outerHTML"
            )

            return extract_uuid(html)

        except WebDriverException:
            return None

    @staticmethod
    def name(row) -> str:

        selectors = [
            "[id^='nome_documento_']",
            ".nome_documento",
            "[class*='nome_documento']",
        ]

        for selector in selectors:

            try:

                elements = row.find_elements(
                    By.CSS_SELECTOR,
                    selector,
                )

                for element in elements:

                    text = element.text.strip()

                    if text:
                        return text

            except WebDriverException:
                continue

        try:

            lines = [
                line.strip()
                for line in row.text.splitlines()
                if line.strip()
            ]

            for line in lines:

                lower = line.lower()

                if (
                    "finalizado" not in lower
                    and "download" not in lower
                ):
                    return line

        except WebDriverException:
            pass

        return "documento"

    @staticmethod
    def finalized(row) -> bool:

        selectors = [
            ".label-finalizado",
            ".finalizado",
            "[class*='finalizado']",
        ]

        for selector in selectors:

            try:

                if row.find_elements(
                    By.CSS_SELECTOR,
                    selector,
                ):
                    return True

            except WebDriverException:
                pass

        return True

    @staticmethod
    def download_element(row):

        try:

            elements = row.find_elements(
                By.CSS_SELECTOR,
                "a, button, input",
            )

        except WebDriverException:
            return None

        best = None
        best_score = 0

        for element in elements:

            try:

                text = element.text.lower()

                href = (
                    element.get_attribute("href")
                    or ""
                )

                onclick = (
                    element.get_attribute("onclick")
                    or ""
                )

                title = (
                    element.get_attribute("title")
                    or ""
                )

                value = (
                    element.get_attribute("value")
                    or ""
                )

                combined = (
                    f"{text} "
                    f"{href} "
                    f"{onclick} "
                    f"{title} "
                    f"{value}"
                ).lower()

                score = 0

                if "apenas assinaturas" in combined:
                    score += 100

                if "download" in combined:
                    score += 50

                if "gerardownload" in combined:
                    score += 50

                if "baixar" in combined:
                    score += 40

                if "pdf" in combined:
                    score += 20

                if score > best_score:

                    best = element
                    best_score = score

            except WebDriverException:
                continue

        return best