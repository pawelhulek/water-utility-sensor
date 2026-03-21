"""WODKAN Krzeszowice water utility provider."""
import re
from datetime import datetime
from typing import Optional

import httpx
from playwright.sync_api import sync_playwright

from . import WaterProvider, WaterReading, AccountBalance, ProviderInfo, ProviderRegistry


@ProviderRegistry.register
class WodkanKrzeszowiceProvider(WaterProvider):
    """Provider for WODKAN Krzeszowice (ibo.wikkrzeszowice.pl)."""

    BASE_URL = "https://ibo.wikkrzeszowice.pl/client"
    LOGIN_URL = "https://ibo.wikkrzeszowice.pl/client/Login.aspx"

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="wodkan_krzeszowice",
            name="WODKAN Krzeszowice",
            description="Wodociągi i Kanalizacja Krzeszowice",
        )

    def __init__(self, client_code: str, password: str):
        self.client_code = client_code
        self.password = password
        self._cookies: dict = {}

    def login(self) -> bool:
        """Login to WODKAN IBO."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(self.LOGIN_URL, wait_until="networkidle")
            page.fill("#tbUserName_I", self.client_code)
            page.fill("#tbPassword_I", self.password)
            page.click("#btLogin")
            page.wait_for_load_state("networkidle")

            try:
                page.click('text="Rozumiem"')
                page.wait_for_timeout(1000)
            except Exception:
                pass

            cookies = context.cookies()
            self._cookies = {c["name"]: c["value"] for c in cookies}

            browser.close()

        return len(self._cookies) > 0

    def get_invoice_ids(self) -> list[tuple[str, str]]:
        """Get list of invoice IDs from Faktury page."""
        if not self._cookies:
            self.login()

        client = httpx.Client(cookies=self._cookies, follow_redirects=True)
        response = client.get(f"{self.BASE_URL}/Faktury.aspx")

        pattern = r'PobierzDok\.aspx\?idFak=(\d+)(?:&|&amp;)typ=1'
        matches = re.findall(pattern, response.text)

        seen = set()
        unique_ids = []
        for mid in matches:
            if mid not in seen:
                seen.add(mid)
                unique_ids.append((f"idFak={mid}&typ=1", mid))

        client.close()
        return unique_ids

    def download_invoice(self, invoice_id: str) -> bytes:
        """Download an invoice PDF."""
        if not self._cookies:
            self.login()

        client = httpx.Client(cookies=self._cookies, follow_redirects=True)
        url = f"{self.BASE_URL}/PobierzDok.aspx?{invoice_id}"
        response = client.get(url)
        client.close()

        if response.status_code == 200 and b"%PDF" in response.content[:10]:
            return response.content
        return b""

    def _parse_invoice(self, pdf_bytes: bytes) -> Optional[WaterReading]:
        """Parse water reading from invoice PDF."""
        try:
            import fitz

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = doc[0].get_text()
            doc.close()

            period_match = re.search(
                r'(\d{2})-(\d{2})-(\d{2})\s*-\s*(\d{2})-(\d{2})-(\d{2})',
                text
            )

            if period_match:
                period_end = datetime(
                    2000 + int(period_match.group(6)),
                    int(period_match.group(5)),
                    int(period_match.group(4))
                )
            else:
                period_end = datetime.now()

            water_section_match = re.search(
                r'Woda\s+gospodarcza.*?(?=Słownie|Woda\s+PKWiU)',
                text,
                re.DOTALL | re.IGNORECASE
            )

            if not water_section_match:
                return None

            section = water_section_match.group(0)

            meter_match = re.search(r'([A-Z]{2,}\d+)', section)
            meter_number = meter_match.group(1) if meter_match else ""

            reading_candidates = []
            lines = section.split('\n')
            for line in lines:
                stripped = line.strip()
                if re.match(r'^\d{3,}$', stripped):
                    reading_candidates.append(int(stripped))

            if len(reading_candidates) >= 2:
                previous_reading = float(reading_candidates[-2])
                current_reading = float(reading_candidates[-1])
            elif len(reading_candidates) == 1:
                current_reading = float(reading_candidates[0])
                previous_reading = 0
            else:
                return None

            consumption = current_reading - previous_reading

            return WaterReading(
                timestamp=period_end,
                current_reading=current_reading,
                previous_reading=previous_reading,
                consumption=consumption,
                meter_number=meter_number
            )

        except Exception:
            return None

    def get_current_reading(self) -> Optional[WaterReading]:
        """Get the most recent water reading from invoices."""
        invoice_ids = self.get_invoice_ids()

        if not invoice_ids:
            return None

        for url_id, _ in invoice_ids:
            pdf_bytes = self.download_invoice(url_id)
            if pdf_bytes:
                reading = self._parse_invoice(pdf_bytes)
                if reading and reading.consumption > 0:
                    return reading

        return None

    def get_account_balance(self) -> Optional[AccountBalance]:
        """Get account balance from default page."""
        if not self._cookies:
            self.login()

        client = httpx.Client(cookies=self._cookies, follow_redirects=True)
        response = client.get(f"{self.BASE_URL}/Default.aspx")
        client.close()

        pattern = r'(\d+[\.,]\d+)\s*zł'
        match = re.search(pattern, response.text)

        if match:
            amount = float(match.group(1).replace(",", "."))

            if "niedopłata" in response.text.lower():
                status = "niedopłata"
            elif "nadpłata" in response.text.lower():
                status = "nadpłata"
            else:
                status = "ok"

            return AccountBalance(amount=amount, status=status)

        return None
